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

from openerp import models, fields, api


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
