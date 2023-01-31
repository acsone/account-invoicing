# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import ValidationError


class OneVatMixin(models.AbstractModel):
    _name = "one.vat.mixin"
    _description = "Abstract the methods needed to ensure only one VAT tax is selected."

    def _check_only_one_vat_tax_field(self, field_name):
        for rec in self:
            if rec.company_id.account_tax_one_vat:
                vat_taxes = rec[field_name].filtered(lambda r: r.is_vat)
                if len(vat_taxes) > 1:
                    msg = _(
                        "Multiple taxes of type VAT are selected. Only one is allowed."
                    )
                    raise ValidationError(msg)

    def _onchange_one_vat_tax_field(self, field_name):
        """Warning if multiple VAT taxes are selected."""
        if self.company_id.account_tax_one_vat:
            try:
                self._check_only_one_vat_tax_field(field_name)
            except ValidationError:
                warning_mess = {
                    "title": _("More than one VAT tax selected!"),
                    "message": _("You selected more than one tax of type VAT."),
                }
                return {"warning": warning_mess}
        return {}
