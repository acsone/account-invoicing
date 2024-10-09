# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo.tests import Form
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon


class TestStockAccountMoveMultiResetToDraft(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env["product.category"].create(
            {
                "name": "Test product",
                "property_cost_method": "average",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test product",
                "categ_id": cls.category.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test partner"})

    @mute_logger("odoo.models.unlink")
    def test_purchase_order_flow(self):
        order_form = Form(self.env["purchase.order"])
        order_form.partner_id = self.partner
        with order_form.order_line.new() as line_form:
            line_form.product_id = self.product
            line_form.price_unit = 10
            line_form.taxes_id.clear()
        order = order_form.save()
        order.button_confirm()
        res = order.picking_ids.button_validate()
        wizard = self.env[res["res_model"]].with_context(**res["context"]).create({})
        wizard.process()
        self.assertEqual(order.picking_ids.state, "done")
        res_invoice = order.action_create_invoice()
        invoice = self.env[res_invoice["res_model"]].browse(res_invoice["res_id"])
        self.assertEqual(invoice.state, "draft")
        invoice.invoice_date = order.date_approve
        invoice.invoice_line_ids.price_unit = 12
        # Upon confirmation, a SVL will be created for the difference (2=12-10)
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(len(invoice.invoice_line_ids.stock_valuation_layer_ids), 1)
        svl_1 = invoice.invoice_line_ids.stock_valuation_layer_ids
        self.assertEqual(svl_1.value, 2)
        self.assertEqual(
            sum(invoice.invoice_line_ids.mapped("stock_valuation_layer_ids.value")), 2
        )
        self.assertTrue(invoice.show_reset_to_draft_button)
        # Switch to draft, a SVL will be created for the difference
        invoice.button_draft()
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(len(invoice.invoice_line_ids.stock_valuation_layer_ids), 2)
        self.assertEqual(svl_1.value, 2)
        svl_1_negative = invoice.invoice_line_ids.stock_valuation_layer_ids - svl_1
        self.assertEqual(svl_1_negative.value, -2)
        self.assertEqual(
            sum(invoice.invoice_line_ids.mapped("stock_valuation_layer_ids.value")), 0
        )
        # Confirm again, no new SVLs are generated
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(len(invoice.invoice_line_ids.stock_valuation_layer_ids), 2)
        self.assertEqual(svl_1.value, 2)
        self.assertEqual(svl_1_negative.value, -2)
        self.assertTrue(invoice.show_reset_to_draft_button)
        self.assertEqual(
            sum(invoice.invoice_line_ids.mapped("stock_valuation_layer_ids.value")), 0
        )
        # Change to draft and change the price to 10 so that SVL is not generated
        invoice.button_draft()
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(len(invoice.invoice_line_ids.stock_valuation_layer_ids), 2)
        self.assertEqual(svl_1.value, 2)
        self.assertEqual(svl_1_negative.value, -2)
        invoice.invoice_line_ids.price_unit = 10
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertEqual(len(invoice.invoice_line_ids.stock_valuation_layer_ids), 2)
        self.assertEqual(svl_1.value, 2)
        self.assertEqual(svl_1_negative.value, -2)
        self.assertTrue(invoice.show_reset_to_draft_button)
        self.assertEqual(
            sum(invoice.invoice_line_ids.mapped("stock_valuation_layer_ids.value")), 0
        )
