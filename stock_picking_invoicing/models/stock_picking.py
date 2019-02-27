# -*- coding: utf-8 -*-
# Copyright (C) 2019-Today: Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = [
        _name,
        "stock.invoice.state.mixin",
    ]

    invoice_ids = fields.Many2many(
        comodel_name="account.invoice",
        relation="stock_picking_account_invoice_m2m",
        column1="picking_id",
        column2="invoice_id",
        readonly=True,
    )

    @api.multi
    def set_to_be_invoiced(self):
        """
        Update invoice_state of current pickings to "2binvoiced".
        :return: bool
        """
        pickings_to_update = self.browse()
        for pick in self:
            if pick.invoice_state in ('none', 'invoiced') and pick.invoice_ids:
                params = (pick.name, pick.invoice_id.number)
                raise UserError(_("Picking %s is already linked to "
                                  "invoice %s") % params)
            pickings_to_update |= pick
        # To avoid too many re-computation, execute update on many records
        pickings_to_update._set_as_2binvoiced()
        return True

    @api.multi
    def _set_as_2binvoiced(self):
        """
        Inherit to also update related moves.
        :return: bool
        """
        self.mapped("move_lines")._set_as_2binvoiced()
        return super(StockPicking, self)._set_as_2binvoiced()

    @api.multi
    def _set_as_invoiced(self):
        """
        Inherit to also update related moves.
        :return: bool
        """
        self.mapped("move_lines")._set_as_invoiced()
        return super(StockPicking, self)._set_as_invoiced()

    @api.multi
    def set_invoiced(self):
        """
        Update invoice_state of current pickings to "invoiced".
        :return:
        """
        pickings_to_update = self.browse()
        for picking in self:
            if picking.invoice_state == 'invoiced' or picking.invoice_id:
                raise UserError(
                    _('Invoice control cannot be updated for picking %s as it '
                      'is already set as "Invoiced"') % picking.name)
            if picking.invoice_state == '2binvoiced' and picking.invoice_id:
                params = (picking.name, picking.invoice_id.number)
                raise UserError(
                    _('Picking %s is already linked to invoice %s') % params)
            pickings_to_update |= picking
        # To avoid too many re-computation, execute update on many records
        pickings_to_update._set_as_invoiced()
        return True

    @api.multi
    def _create_invoice_from_picking(self, picking, vals):
        """
        This function simply creates the invoice from the given values and
        attach it to given picking
        It is overridden in delivery module to add the delivery costs.
        :param picking: stock.picking recordset
        :param vals: dict
        :return: account.invoice recordset
        """
        _logger.debug("Create invoice with %s", vals)
        invoice = self.env['account.invoice'].create(vals)
        if picking:
            picking.write({
                'invoice_ids': [(4, invoice.id, False)],
                'invoice_state': 'invoiced',
            })
        return invoice

    @api.multi
    def _get_partner_to_invoice(self):
        partner = self.partner_id
        return partner.address_get(['invoice']).get('invoice')

    @api.multi
    def _get_invoice_vals(self, key, inv_type, journal_id, move):
        partner, currency_id, company_id, user_id = key
        if inv_type in ('out_invoice', 'out_refund'):
            account_id = partner.property_account_receivable_id.id
            payment_term = partner.property_payment_term_id.id
        else:
            account_id = partner.property_account_payable_id.id
            payment_term = partner.property_supplier_payment_term_id.id
        return {
            'origin': move.picking_id.name,
            'date_invoice': self.env.context.get('date_inv', False),
            'user_id': user_id,
            'partner_id': partner.id,
            'account_id': account_id,
            'payment_term_id': payment_term,
            'type': inv_type,
            'fiscal_position_id': partner.property_account_position_id.id,
            'company_id': company_id,
            'currency_id': currency_id,
            'journal_id': journal_id,
        }

    @api.model
    def _invoice_create_line(self, moves, journal_id, inv_type='out_invoice'):
        """
        Create an invoice and associated lines
        :param moves: stock.move recordset
        :param journal_id:
        :param inv_type: str
        :return: account.invoice recordset
        """
        move_obj = self.env['stock.move']
        invoices_dict = {}
        context = self.env.context
        is_extra_move, extra_move_tax = move_obj._get_moves_taxes(moves)
        product_price_unit = {}
        _logger.debug("Context: %s", context)
        invoice = None
        company = self.env.user.company_id
        force_company = context.get('force_company')
        if context.get('force_company'):
            company = self.env['res.company'].browse(force_company)
        for move in moves:
            origin = move.picking_id.name
            partner, user_id, currency_id = move_obj._get_master_data(
                move, company)
            key = (partner, currency_id, company.id, user_id)
            invoice_vals = self._get_invoice_vals(
                key, inv_type, journal_id, move)
            if key not in invoices_dict:
                # Get account and payment terms
                _logger.debug("Add invoice to list")
                invoice = self._create_invoice_from_picking(
                    move.picking_id, invoice_vals)
                invoices_dict[key] = invoice
                _logger.debug("Add invoice to list after key")
            else:
                _logger.debug("Add found invoice to list")
                invoice = invoices_dict.get(key)
                merge_vals = {}
                origins = (invoice.origin or '').split(', ')
                if not invoice.origin or invoice_vals['origin'] not in origins:
                    invoice_origin = filter(
                        None, [invoice.origin, invoice_vals['origin']])
                    merge_vals['origin'] = ', '.join(invoice_origin)
                name_split = (invoice.name or '').split(', ')
                if invoice_vals.get('name', False) and \
                        (invoice_vals['name'] not in name_split):
                    invoice_name = filter(
                        None, [invoice.name, invoice_vals['name']])
                    merge_vals['name'] = ', '.join(invoice_name)
                if merge_vals:
                    _logger.debug("Merge vues %s", merge_vals)
                    invoice.write(merge_vals)

            if invoice_vals.get('fiscal_position_id'):
                move = move.with_context(
                    fp_id=invoice_vals.get('fiscal_position_id', False))

            invoice_line_vals = move._get_invoice_line_vals(partner, inv_type)
            invoice_line_vals.update({
                'invoice_id': invoices_dict[key].id,
                'origin': origin,
            })
            current_key = invoice_line_vals.get(
                'product_id'), invoice_line_vals.get('uom_id')
            if not is_extra_move[move.id]:
                product_price_unit[current_key] = invoice_line_vals[
                    'price_unit']
            if is_extra_move[move.id] and current_key in product_price_unit:
                invoice_line_vals['price_unit'] = product_price_unit[
                    current_key]
            if is_extra_move[move.id]:
                desc = (inv_type in ('out_invoice', 'out_refund') and
                        move.product_id.product_tmpl_id.description_sale) or \
                       (inv_type in ('in_invoice', 'in_refund') and
                        move.product_id.product_tmpl_id.description_purchase)
                invoice_line_vals['name'] += ' ' + desc if desc else ''
                if extra_move_tax[move.picking_id, move.product_id]:
                    invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[
                        move.picking_id, move.product_id]
                # The default product taxes
                elif (0, move.product_id) in extra_move_tax:
                    invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[
                        0, move.product_id]

            invoice_line = move._create_invoice_line_from_vals(
                invoice_line_vals)
            _logger.debug("Before invoicing write")
            if invoice_line:
                move.write({
                    'invoice_line_ids': [(4, invoice_line.id, False)],
                    'invoice_state': 'invoiced',
                })
            if move.picking_id and not move.picking_id.invoice_ids:
                move.picking_id.write({
                    'invoice_ids': [(4, invoice.id, False)],
                    'invoice_state': 'invoiced',
                })
        invoice._force_compute_invoice_tax_lines()
        invoices = self.env['account.invoice'].browse()
        for new_invoices in invoices_dict.values():
            invoices |= new_invoices
        return invoices

    @api.multi
    def _get_group_key_to_invoice(self):
        """
        Get the key (during grouping) invoice creation
        :return: tuple
        """
        self.ensure_one()
        return self._get_partner_to_invoice()

    @api.multi
    def action_invoice_create(
            self, journal_id, group=False, inv_type='out_invoice'):
        """
        Creates invoice based on the invoice state selected for picking.
        :param journal_id: int
        :param group: bool
        :param inv_type: str
        :return: account.invoice recordset
        """
        todo = {}
        for picking in self:
            key = picking.id
            if group:
                key = self._get_group_key_to_invoice()

            for move in picking.move_lines:
                if move.invoice_state == '2binvoiced':
                    if (move.state != 'cancel') and not move.scrapped:
                        moves = todo.get(key, self.env['stock.move'].browse())
                        moves |= move
                        todo.update({
                            key: moves,
                        })
        invoices = self.env['account.invoice'].browse()
        for moves in todo.values():
            invoices |= self._invoice_create_line(moves, journal_id, inv_type)
        return invoices
