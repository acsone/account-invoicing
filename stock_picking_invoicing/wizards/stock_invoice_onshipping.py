# -*- coding: utf-8 -*-
# Copyright (C) 2019-Today: Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, fields, api, _
from odoo.exceptions import UserError


JOURNAL_TYPE_MAP = {
    ('outgoing', 'customer'): ['sale'],
    ('outgoing', 'supplier'): ['purchase_refund'],
    ('outgoing', 'transit'): ['sale', 'purchase_refund'],
    ('incoming', 'supplier'): ['purchase'],
    ('incoming', 'customer'): ['sale_refund'],
    ('incoming', 'transit'): ['purchase', 'sale_refund'],
}


class StockInvoiceOnshipping(models.TransientModel):
    _name = 'stock.invoice.onshipping'
    _description = "Stock Invoice Onshipping"

    @api.model
    def view_init(self, fields_list):
        res = super(StockInvoiceOnshipping, self).view_init(fields_list)
        pick_obj = self.env['stock.picking']
        active_ids = self.env.context.get('active_ids', [])
        domain = [
            ('id', 'in', active_ids),
            ('invoice_state', '!=', '2binvoiced'),
            ('partner_id', '=', False),
        ]
        if pick_obj.search_count(domain):
            raise UserError(
                _('All your pickings must have a partner to be invoiced!'))
        return res

    @api.multi
    def check_to_be_invoiced(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids', [])
        pick_obj = self.env['stock.picking']
        domain = [
            ('id', 'in', active_ids),
            ('invoice_state', '!=', '2binvoiced'),
        ]
        pick_count = pick_obj.search_count(domain)
        if len(active_ids) == pick_count and not self.invoice_force:
            self.invoice_force = True
            raise UserError(_('None of these picking require invoicing.\n'
                              'You need to force the invoicing.'))

    @api.onchange('group')
    def onchange_group(self):
        self.ensure_one()
        sale_pickings, sale_refund_pickings, purchase_pickings,\
            purchase_refund_pickings = self.get_split_pickings()
        self.show_sale_journal = bool(sale_pickings)
        self.show_sale_refund_journal = bool(sale_refund_pickings)
        self.show_purchase_journal = bool(purchase_pickings)
        self.show_purchase_refund_journal = bool(purchase_refund_pickings)

    @api.model
    def _default_journal(self, journal_type):
        default_journal = self.env['account.journal'].search([
            ('type', '=', journal_type),
            ('company_id', '=', self.env.user.company_id.id),
        ], limit=1)
        return default_journal

    @api.model
    def _get_journal(self):
        journal_type = self._get_journal_type()
        return self._default_journal(journal_type)

    @api.model
    def _get_journal_type(self):
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            active_ids = active_ids[0]
        pick_obj = self.env['stock.picking']
        picking = pick_obj.browse(active_ids)
        if not picking or not picking.move_lines:
            return 'sale'
        pick_type_code = picking.picking_type_id.code
        line = fields.first(picking.move_lines)
        if pick_type_code == 'incoming':
            usage = line.location_id.usage
        else:
            usage = line.location_dest_id.usage
        return JOURNAL_TYPE_MAP.get((pick_type_code, usage), ['sale'])[0]

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Destination Journal',
        default=_get_journal,
        required=False,
    )
    journal_type = fields.Selection(
        selection=[
            ('purchase_refund', 'Refund Purchase'),
            ('purchase', 'Create Supplier Invoice'),
            ('sale_refund', 'Refund Sale'),
            ('sale', 'Create Customer Invoice')
        ],
        default=_get_journal_type,
        readonly=True,
    )
    group = fields.Boolean(
        string="Group by partner",
    )
    invoice_date = fields.Date()
    invoice_force = fields.Boolean(
        string='Force Invoicing',
        default=False,
    )
    sale_journal = fields.Many2one(
        comodel_name='account.journal',
        domain="[('type', '=', 'sale')]",
        default=lambda self: self._default_journal('sale'),
    )
    sale_refund_journal = fields.Many2one(
        comodel_name='account.journal',
        domain="[('type', '=', 'sale_refund')]",
        default=lambda self: self._default_journal('sale_refund'),
    )
    purchase_journal = fields.Many2one(
        comodel_name='account.journal',
        domain="[('type', '=', 'purchase')]",
        default=lambda self: self._default_journal('purchase'),
    )
    purchase_refund_journal = fields.Many2one(
        comodel_name='account.journal',
        domain="[('type', '=', 'purchase_refund')]",
        default=lambda self: self._default_journal('purchase_refund'),
    )
    show_sale_journal = fields.Boolean()
    show_sale_refund_journal = fields.Boolean(
        string="Show Refund Sale Journal",
    )
    show_purchase_journal = fields.Boolean()
    show_purchase_refund_journal = fields.Boolean(
        string="Show Refund Purchase Journal",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string='Company to invoice',
        default=lambda self: self.env.user.company_id.id,
    )

    @api.multi
    def open_invoice(self):
        self.ensure_one()
        self.check_to_be_invoiced()
        invoices = self.create_invoice()
        if not invoices:
            raise UserError(_('No invoice created!'))

        journal2type = {
            'sale': 'out_invoice',
            'purchase': 'in_invoice',
            'sale_refund': 'out_refund',
            'purchase_refund': 'in_refund',
        }
        inv_type = journal2type.get(self.journal_type) or 'out_invoice'
        data_pool = self.env['ir.actions.act_window']

        if inv_type in ["out_invoice", "out_refund"]:
            action_dict = data_pool.for_xml_id(
                'account', 'action_invoice_tree1')
        elif inv_type == "in_invoice":
            action_dict = data_pool.for_xml_id(
                'account', 'action_invoice_tree2')

        if action_dict:
            action = action_dict.copy()
            action.update({
                'domain': [('id', 'in', invoices.ids)],
            })
            return action
        return {}

    @api.multi
    def create_invoice(self):
        """

        :return: account.invoice recordset
        """
        self.ensure_one()
        picking_obj = self.env['stock.picking']
        journal2type = {
            'sale': 'out_invoice',
            'purchase': 'in_invoice',
            'sale_refund': 'out_refund',
            'purchase_refund': 'in_refund',
        }
        inv_type = journal2type.get(self.journal_type) or 'out_invoice'
        active_ids = self.env.context.get('active_ids', [])
        pickings = picking_obj.browse(active_ids)
        if self.invoice_force:
            pickings.set_invoiced()

        force_company_id = self.company_id.id or self.env.user.company_id.id
        pickings = pickings.with_context(
            date_inv=self.invoice_date,
            inv_type=inv_type,
            force_company=force_company_id,
        )
        invoices = pickings.action_invoice_create(
            journal_id=self.journal_id.id, group=self.group, inv_type=inv_type)
        return invoices

    @api.multi
    def get_partner_sum(
            self, pickings, partner, inv_type, picking_type, usage):
        pickings = pickings.filtered(
            lambda x: x.picking_type_id.code == picking_type and
            x.partner_id == partner)
        lines = pickings.mapped('move_lines')
        if picking_type == 'outgoing':
            moves = lines.filtered(lambda x: x.location_dest_id.usage == usage)
        else:
            moves = lines.filtered(lambda x: x.location_id.usage == usage)
        total = sum([(m._get_price_unit_invoice(inv_type) * m.product_uom_qty)
                     for m in moves])
        return total, moves.mapped('picking_id')

    @api.multi
    def get_split_pickings_grouped(self, pickings):
        sale_pickings = self.env['stock.picking']
        sale_refund_pickings = self.env['stock.picking']
        purchase_pickings = self.env['stock.picking']
        purchase_refund_pickings = self.env['stock.picking']

        for partner in pickings.mapped('partner_id'):
            so_sum, so_pickings = self.get_partner_sum(
                pickings, partner, 'out_invoice', 'outgoing', 'customer')
            si_sum, si_pickings = self.get_partner_sum(
                pickings, partner, 'out_invoice', 'incoming', 'customer')
            if (so_sum - si_sum) >= 0:
                sale_pickings |= (so_pickings | si_pickings)
            else:
                sale_refund_pickings |= (so_pickings | si_pickings)
            pi_sum, pi_pickings = self.get_partner_sum(
                pickings, partner, 'in_invoice', 'incoming', 'supplier')
            po_sum, po_pickings = self.get_partner_sum(
                pickings, partner, 'in_invoice', 'outgoing', 'supplier')
            if (pi_sum - po_sum) >= 0:
                purchase_pickings |= (pi_pickings | po_pickings)
            else:
                purchase_refund_pickings |= (pi_pickings | po_pickings)
        return (sale_pickings, sale_refund_pickings, purchase_pickings,
                purchase_refund_pickings)

    @api.multi
    def get_split_pickings_nogrouped(self, pickings):
        first = fields.first
        sale_pickings = pickings.filtered(
            lambda x: x.picking_type_id.code == 'outgoing' and
            first(x.move_lines).location_dest_id.usage == 'customer')
        # use [:1] instead of [0] to avoid a errors on empty pickings
        sale_refund_pickings = pickings.filtered(
            lambda x: x.picking_type_id.code == 'incoming' and
            first(x.move_lines).location_id.usage == 'customer')
        purchase_pickings = pickings.filtered(
            lambda x: x.picking_type_id.code == 'incoming' and
            first(x.move_lines).location_id.usage == 'supplier')
        purchase_refund_pickings = pickings.filtered(
            lambda x: x.picking_type_id.code == 'outgoing' and
            first(x.move_lines).location_dest_id.usage == 'supplier')

        return (sale_pickings, sale_refund_pickings, purchase_pickings,
                purchase_refund_pickings)

    @api.multi
    def get_split_pickings(self):
        self.ensure_one()
        picking_obj = self.env['stock.picking']
        pickings = picking_obj.browse(self.env.context.get('active_ids', []))
        if self.group:
            return self.get_split_pickings_grouped(pickings)
        return self.get_split_pickings_nogrouped(pickings)
