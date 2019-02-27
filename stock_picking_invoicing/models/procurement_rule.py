# -*- coding: utf-8 -*-
# Copyright (C) 2019-Today: Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class ProcurementRule(models.Model):
    _name = 'procurement.rule'
    _inherit = [
        _name,
        "stock.invoice.state.mixin",
    ]
