# -*- coding: utf-8 -*-
#
##############################################################################
#
#     Authors: Adrien Peiffer
#    Copyright (c) 2015 Acsone SA/NV (http://www.acsone.eu)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    disable_taxes_check = fields.Boolean(string="Disable "
                                         "taxes check (be careful !)",
                                         readonly=True,
                                         states={'draft':
                                                 [('readonly', False)]})

    @api.multi
    def check_tax_lines(self, compute_taxes):
        if not self.disable_taxes_check:
            super(account_invoice, self).check_tax_lines(compute_taxes)

    @api.multi
    def action_move_create(self):
        """ Adapt the created move in case of modification of base's column
            on account invoice tax lines"""
        res = super(account_invoice, self).action_move_create()
        aml_obj = self.env['account.move.line']
        for invoice in self:
            if invoice.disable_taxes_check:
                compare = {}
                tax_code_account_mapping = {}
                if invoice.move_id.id:
                    for line in invoice.tax_line:
                        if line.base_code_id.id and line.account_id.id:
                            key = line.base_code_id.id
                            if compare.get(key, False):
                                compare[key] += line.base
                            else:
                                compare[key] = line.base
                    for line in invoice.move_id.line_id:
                        key = line.tax_code_id.id
                        if compare.get(key, False):
                            # Here, we get difference between tax lines and
                            # move lines
                            compare[key] -= line.tax_amount
                            if not tax_code_account_mapping.get(key, False):
                                tax_code_account_mapping[key] = \
                                    line.account_id.id
                    for tax_code_id, amount in compare.iteritems():
                        if amount != 0.0:
                            aml_data = {
                                'type': 'tax',
                                'name': _('Tax Adjustment'),
                                'credit': 0.0,
                                'account_id':
                                    tax_code_account_mapping[tax_code_id],
                                'tax_code_id': tax_code_id,
                                'tax_amount': amount,
                                'move_id': invoice.move_id.id,
                            }
                            aml_obj.with_context(from_parent_object=True)\
                                .create(aml_data)
        return res
