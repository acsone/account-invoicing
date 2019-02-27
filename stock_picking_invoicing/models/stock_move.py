# -*- coding: utf-8 -*-
# Copyright (C) 2019-Today: Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, api, fields


class StockMove(models.Model):
    _name = "stock.move"
    _inherit = [
        _name,
        "stock.invoice.state.mixin",
    ]

    invoice_line_id = fields.Many2one(
        comodel_name='account.invoice.line',
        string='Invoice Line',
        readonly=True,
    )
    invoice_id = fields.Many2one(
        comodel_name='account.invoice',
        string='Invoice',
        related='invoice_line_id.invoice_id',
        related_sudo=False,
        readonly=True,
        store=True,
    )

    @api.model
    def _create_invoice_line_from_vals(self, invoice_line_vals):
        """
        Create a new invoice line using given values
        :param invoice_line_vals: dict
        :return: account.invoice.line recordset
        """
        return self.env['account.invoice.line'].create(invoice_line_vals)

    @api.multi
    def get_code_from_locs(self, location_id=False, location_dest_id=False):
        """
        Copy/Paste from odoo v9.0 stock.move
        Returns the code the picking type should have.
        This can easily be used to check if a move is internal or not
        move, location_id and location_dest_id are browse records
        :param location_id: int
        :param location_dest_id: int
        :return: str
        """
        self.ensure_one()
        code = 'internal'
        src_loc = location_id or self.location_id
        dest_loc = location_dest_id or self.location_dest_id
        if src_loc.usage == 'internal' and dest_loc.usage != 'internal':
            code = 'outgoing'
        if src_loc.usage != 'internal' and dest_loc.usage == 'internal':
            code = 'incoming'
        return code

    @api.model
    def _get_master_data(self, move, company):
        """
        Based on the move and the company, build a key.
        returns a tuple:
        (res.partner,  ID(res.users), ID(res.currency)
        :param move: stock.move recordset
        :param company: res.company recordset
        :return: tuple (res.partner, int, int)
        """
        currency = company.currency_id.id
        partner = move.picking_id.partner_id
        if partner:
            code = move.get_code_from_locs()
            if partner.property_product_pricelist and code == 'outgoing':
                currency = partner.property_product_pricelist.currency_id.id
        data = partner, self.env.uid, currency

        if move.picking_id.partner_id != partner:
            # if someone else modified invoice partner, I use it
            return data

        partner_invoice_id = move.picking_id.partner_id.address_get(
            ['invoice']).get('invoice')
        partner = self.env['res.partner'].browse(partner_invoice_id)
        new_data = partner, self.env.uid, currency
        return new_data

    @api.multi
    def _get_taxes(self, fiscal_position):
        """
        Map product taxes based on given fiscal position
        :param fiscal_position: account.fiscal.position recordset
        :return: account.tax recordset
        """
        self.ensure_one()
        taxes = self.product_id.taxes_id
        company_id = self.env.context.get(
            'force_company', self.env.user.company_id.id)
        my_taxes = taxes.filtered(lambda r: r.company_id.id == company_id)
        return fiscal_position.map_tax(my_taxes)

    @api.model
    def _get_account(self, fiscal_position, account):
        """
        Map the given account with given fiscal position
        :param fiscal_position: account.fiscal.position recordset
        :param account: account.account recordset
        :return: account.account recordset
        """
        return fiscal_position.map_account(account)

    @api.multi
    def _get_invoice_line_vals(self, partner, inv_type):
        """
        Build invoice line values dict
        :param partner: res.partner recordset
        :param inv_type: str
        :return: dict
        """
        self.ensure_one()
        fisc_pos_obj = self.env['account.fiscal.position']
        # Get account_id
        fisc_pos = fisc_pos_obj.browse(self.env.context.get('fp_id', []))
        categ = self.product_id.categ_id
        name = False
        if inv_type in ('out_invoice', 'out_refund'):
            account = self.product_id.property_account_income_id
            if not account:
                account = categ.property_account_income_categ_id
            if self.procurement_id and self.procurement_id.sale_line_id:
                name = self.procurement_id.sale_line_id.name
        else:
            account = self.product_id.property_account_expense_id
            if not account:
                account = categ.property_account_expense_categ_id
        fiscal_position = fisc_pos or partner.property_account_position_id
        account = self._get_account(fiscal_position, account)
        uom_id = self.product_uom.id
        quantity = self.product_uom_qty
        taxes = self._get_taxes(fiscal_position)
        loc = self.location_id
        loc_dst = self.location_dest_id
        # negative value on quantity
        if ((inv_type == 'out_invoice' and loc.usage == 'customer') or
                (inv_type == 'out_refund' and loc_dst.usage == 'customer') or
                (inv_type == 'in_invoice' and loc_dst.usage == 'supplier') or
                (inv_type == 'in_refund' and loc.usage == 'supplier')):
            quantity *= -1
        values = {
            'name': name or (self.picking_id.name + '\n' + self.name),
            'account_id': account.id,
            'product_id': self.product_id.id,
            'uom_id': uom_id,
            'quantity': quantity,
            'price_unit': self._get_price_unit_invoice(inv_type, partner),
            'invoice_line_tax_ids': [(6, 0, taxes.ids)],
            'discount': 0.0,
            'account_analytic_id': False,
        }
        return values

    @api.multi
    def _get_price_unit_invoice(self, inv_type, partner):
        """
        Gets price unit for invoice
        :param inv_type: str
        :param partner: res.partner
        :return: float
        """
        product = self.product_id
        if inv_type in ('in_invoice', 'in_refund'):
            result = product.price
        else:
            # If partner given, search price in its sale pricelist
            if partner and partner.property_product_pricelist:
                product = self.product_id.with_context(
                    partner=self.partner_id.id,
                    quantity=self.product_uom_qty,
                    date=self.date,
                    pricelist=partner.property_product_pricelist.id,
                    uom=self.product_uom.id
                )
                result = product.price
            else:
                result = product.lst_price
        return result

    @api.multi
    def _get_moves_taxes(self, moves):
        """
        Extra moves with the same picking_id and product_id of a move have
        the same taxes
        :param moves: stock.move recordset
        :return:tuple (dict, dict)
        """
        extra_move_tax = {}
        is_extra_move = {}
        for move in moves:
            if move.picking_id:
                is_extra_move.update({
                    move.id: True,
                })
                key = (move.picking_id, move.product_id)
                if key not in extra_move_tax:
                    extra_move_tax.update({
                        key: 0,
                    })
            else:
                is_extra_move.update({
                    move.id: False,
                })
        return is_extra_move, extra_move_tax
