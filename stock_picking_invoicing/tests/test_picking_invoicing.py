# -*- coding: utf-8 -*-
# Copyright (C) 2019-Today: Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase
from odoo import exceptions


class TestPickingInvoicing(TransactionCase):

    def setUp(self):
        super(TestPickingInvoicing, self).setUp()
        self.picking_model = self.env['stock.picking']
        self.move_model = self.env['stock.move']
        self.invoice_wizard = self.env['stock.invoice.onshipping']
        self.invoice_model = self.env['account.invoice']
        self.partner_model = self.env['res.partner']
        self.partner = self.env.ref('base.res_partner_2')
        self.partner2 = self.env.ref('base.res_partner_address_4')
        self.pick_type_in = self.env.ref("stock.picking_type_in")
        self.location = self.env.ref("stock.stock_location_stock")
        self.location_dest = self.env.ref("stock.stock_location_customers")
        self.product = self.env.ref("product.product_product_10")
        self.journal = self.env['account.journal'].create({
            'name': 'A super journal name',
            'code': 'ABC',
            'type': 'sale',
            'refund_sequence': True,
        })

    def test_0_picking_invoicing(self):
        # setting Agrolait type to default, because it's 'contact' in demo data
        self.partner.write({'type': 'invoice'})
        picking = self.picking_model.create({
            'partner_id': self.partner2.id,
            'picking_type_id': self.pick_type_in.id,
            'location_id': self.location.id,
            'location_dest_id': self.location_dest.id,
        })
        move_vals = {
            'product_id': self.product.id,
            'picking_id': picking.id,
            'location_dest_id': self.location_dest.id,
            'location_id': self.location.id,
            'name': self.product.name,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
        }
        new_move = self.move_model.create(move_vals)
        new_move.onchange_product_id()
        picking.set_to_be_invoiced()
        picking.action_confirm()
        picking.action_assign()
        picking.do_prepare_partial()
        picking.do_transfer()
        self.assertEqual(picking.state, 'done')
        wizard_obj = self.invoice_wizard.with_context(
            active_ids=picking.ids,
            active_model=picking._name,
            active_id=picking.id,
        )
        fields_list = wizard_obj.fields_get().keys()
        wizard_values = wizard_obj.default_get(fields_list)
        wizard_values.update({
            'journal_id': self.journal.id,
        })
        wizard = wizard_obj.create(wizard_values)
        wizard.onchange_group()
        action = wizard.open_invoice()
        domain = action.get('domain', [])
        invoice = self.invoice_model.search(domain)
        self.assertEqual(picking.invoice_state, 'invoiced')
        self.assertEqual(invoice.partner_id, self.partner)

    def test_1_picking_invoicing(self):
        self.partner.write({'type': 'invoice'})
        picking = self.picking_model.create({
            'partner_id': self.partner2.id,
            'picking_type_id': self.pick_type_in.id,
            'location_id': self.location.id,
            'location_dest_id': self.location_dest.id,
        })
        move_vals = {
            'product_id': self.product.id,
            'picking_id': picking.id,
            'location_dest_id': self.location_dest.id,
            'location_id': self.location.id,
            'name': self.product.name,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
        }
        new_move = self.move_model.create(move_vals)
        new_move.onchange_product_id()
        picking.action_confirm()
        picking.action_assign()
        picking.do_prepare_partial()
        picking.do_transfer()
        self.assertEqual(picking.state, 'done')
        wizard_obj = self.invoice_wizard.with_context(
            active_ids=picking.ids,
            active_model=picking._name,
            active_id=picking.id,
        )
        fields_list = wizard_obj.fields_get().keys()
        wizard_values = wizard_obj.default_get(fields_list)
        wizard_values.update({
            'journal_id': self.journal.id,
        })
        wizard = wizard_obj.create(wizard_values)
        wizard.onchange_group()
        with self.assertRaises(exceptions.UserError) as e:
            wizard.open_invoice()
        msg = "None of these picking require invoicing."
        self.assertIn(msg, e.exception.name)

    def test_2_picking_invoicing(self):
        self.partner.write({'type': 'invoice'})
        picking = self.picking_model.create({
            'partner_id': self.partner2.id,
            'picking_type_id': self.pick_type_in.id,
            'location_id': self.location.id,
            'location_dest_id': self.location_dest.id,
        })
        move_vals = {
            'product_id': self.product.id,
            'picking_id': picking.id,
            'location_dest_id': self.location_dest.id,
            'location_id': self.location.id,
            'name': self.product.name,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
        }
        new_move = self.move_model.create(move_vals)
        new_move.onchange_product_id()
        picking.set_to_be_invoiced()
        picking.action_confirm()
        picking.action_assign()
        picking.do_prepare_partial()
        picking.do_transfer()
        self.assertEqual(picking.state, 'done')
        wizard_obj = self.invoice_wizard.with_context(
            active_ids=picking.ids,
            active_model=picking._name,
            active_id=picking.id,
        )
        fields_list = wizard_obj.fields_get().keys()
        wizard_values = wizard_obj.default_get(fields_list)
        wizard_values.update({
            'journal_id': self.journal.id,
            'group': True,
        })
        wizard = wizard_obj.create(wizard_values)
        wizard.onchange_group()
        action = wizard.open_invoice()
        domain = action.get('domain', [])
        invoice = self.invoice_model.search(domain)
        self.assertEqual(picking.invoice_state, 'invoiced')
        self.assertEqual(invoice.partner_id, self.partner)
