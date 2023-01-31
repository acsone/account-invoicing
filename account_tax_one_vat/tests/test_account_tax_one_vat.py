# Copyright 2023 Acsone SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import TestAccountTaxOneVatCommon


@tagged("post_install", "-at_install")
class TestAccountTaxOneVat(TestAccountTaxOneVatCommon):
    def test_move_line_without_limitation(self):
        """
        No warning upon onchange tax_ids
        """
        invoice = self._create_invoice([(100, self.tax_3)])
        move_line = invoice.line_ids[0]
        move_line.tax_ids = [Command.set(self.vat_taxes.ids)]
        action = move_line._onchange_tax_ids()
        self.assertEqual(action, {})
        self.assertEqual(move_line.tax_ids, self.vat_taxes)

    def test_move_line_with_limitation_warning(self):
        """
        - Get a warning upon onchange tax_ids if we try to set 2 VAT taxes
        """
        self.env["res.config.settings"].create({"account_tax_one_vat": True}).execute()
        invoice = self._create_invoice([(100, self.tax_3)])
        move_line = invoice.line_ids[0]
        move_line.tax_ids = [Command.set(self.vat_taxes.ids)]
        action = move_line._onchange_tax_ids()
        self.assertTrue("warning" in action)
        self.assertDictEqual(
            action,
            {
                "warning": {
                    "title": "More than one VAT tax selected!",
                    "message": "You selected more than one tax of type VAT.",
                }
            },
        )
        self.assertEqual(move_line.tax_ids, self.vat_taxes)

    def test_move_line_with_limitation_no_warning(self):
        """
        - No warning upon onchange tax_ids if we try to set 2 taxes but only 1 VAT
          tax
        """
        self.env["res.config.settings"].create({"account_tax_one_vat": True}).execute()
        invoice = self._create_invoice([(100, self.tax_3)])
        move_line = invoice.line_ids[0]
        move_line.tax_ids = [Command.set(self.mixed_taxes.ids)]
        action = move_line._onchange_tax_ids()
        self.assertEqual(action, {})
        self.assertEqual(move_line.tax_ids, self.mixed_taxes)

    def test_product_without_limitation(self):
        """
        No constraint, vat_id and vat_name are not set
        """
        self.product_test.taxes_id = [Command.set(self.vat_taxes.ids)]
        self.assertEqual(self.product_test.taxes_id, self.vat_taxes)
        self.product_test.supplier_taxes_id = [Command.set(self.vat_taxes.ids)]
        self.assertEqual(self.product_test.supplier_taxes_id, self.vat_taxes)
        # vat_id and vat are not set
        self.assertFalse(self.product_test.vat_id)
        self.assertFalse(self.product_test.vat)

    def test_product_with_limitation_constraint(self):
        """
        - The constraint triggers an error trying to set 2 VAT taxes on product
        - vat_id and vat_name are not set
        """
        # set the one vat tax only
        self.env["res.config.settings"].create({"account_tax_one_vat": True}).execute()
        msg = "Multiple customer tax of type VAT are selected. Only one is allowed."
        with self.assertRaises(ValidationError, msg=msg):
            self.product_test.taxes_id = [Command.set(self.vat_taxes.ids)]
        with self.assertRaises(ValidationError, msg=msg):
            self.product_test.supplier_taxes_id = [Command.set(self.vat_taxes.ids)]
        # vat_id and vat are not set
        self.assertFalse(self.product_test.vat_id)
        self.assertFalse(self.product_test.vat)

    def test_product_with_limitation_no_constraint(self):
        """
        - The constraint doesn't trigger the error if we set 2 taxes containing
          only one VAT
        - vat_id and vat_name are well set
        """
        # set the one vat tax only
        self.env["res.config.settings"].create({"account_tax_one_vat": True}).execute()
        self.product_test.taxes_id = [Command.set(self.mixed_taxes.ids)]
        self.assertEqual(self.product_test.taxes_id, self.mixed_taxes)
        self.product_test.supplier_taxes_id = [Command.set(self.mixed_taxes.ids)]
        self.assertEqual(self.product_test.supplier_taxes_id, self.mixed_taxes)
        # vat_id and vat are not set
        self.assertEqual(self.product_test.vat_id, self.vat_tax_1)
        self.assertEqual(self.product_test.vat, self.vat_tax_1.name)
