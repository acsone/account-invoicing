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

    invoice_line_ids = fields.Many2many(
        comodel_name='account.invoice.line',
        relation="stock_move_account_move_line_m2m",
        column1="stock_move_id",
        column2="invoice_line_id",
        string='Invoice Line',
        readonly=True,
    )

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
