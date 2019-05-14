# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
import datetime

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

class DiFactCronWiz(models.TransientModel):
    _name = "di.fact.cron.wiz"
    _description = "Wizard de facturation en arrière plan"    
    
    date_fact = fields.Date(required=True, default=datetime.datetime.today().date(), string="Date de facturation")
    period_fact = fields.Selection([("DEMANDE", "Demande"), ("SEMAINE", "Semaine"),("DECADE", "Décade"),("QUINZAINE","Quinzaine"),("MOIS","Mois")],
                                      default="DEMANDE", string="Périodicité de Facturation", help="Permet de filtrer lors de la facturation")
    date_debut = fields.Date(required=True, default=datetime.date(datetime.date.today().year, datetime.date.today().month, 1), string="Date Début")
    date_fin = fields.Date(required=True, default=datetime.date(datetime.date.today().year, datetime.date.today().month, calendar.mdays[datetime.date.today().month]), string="Date Fin")
    ref_debut = fields.Char(required=True, default=" ", string="Code Tiers Début")
    ref_fin = fields.Char(required=True, default="ZZZZZZZZZZ", string="Code Tiers Fin")
    
    @api.multi
    def di_create_invoices(self, ids, regr):       
        sale_orders = self.env['sale.order'].browse(ids)
        if sale_orders:
            sale_orders.action_invoice_create(grouped=not regr,final=True)       
                            
        for s_o in sale_orders: #pour passer en complètement facturé les commandes avec reliquat
            s_o.action_done()
            
        invoices = sale_orders.mapped('invoice_ids')
        param = self.env['di.param'].search([('di_company_id','=',self.env.user.company_id.id)])
        if param.di_autovalid_fact_ven:
                invoices.action_invoice_open()
        invoices.write({'date_invoice':self.date_fact})                
    
    def create_cron_fact(self):                
        self.env.cr.execute("""SELECT id FROM ir_model 
                                  WHERE model = %s""", (str(self._name),))            
        info = self.env.cr.dictfetchall()  
        if info:
            model_id = info[0]['id']     
        sale_orders = self.env['sale.order']                    
        query_args = {'periodicity_invoice': self.period_fact,'date_debut' : self.date_debut,'date_fin' : self.date_fin, 'ref_debut': self.ref_debut,'ref_fin':self.ref_fin}
        query = """ SELECT  so.id 
                        FROM sale_order so
                        INNER JOIN res_partner rp on rp.id = so.partner_id 
                        WHERE so.invoice_status = 'to invoice' 
                        AND di_livdt between %(date_debut)s AND %(date_fin)s                            
                        AND rp.ref is not null
                        AND rp.di_period_fact = %(periodicity_invoice)s
                        AND rp.ref between %(ref_debut)s AND %(ref_fin)s 
                        AND rp.di_regr_fact is true                       
                        order by so.partner_id
                        """

        self.env.cr.execute(query, query_args)
        ids = [r[0] for r in self.env.cr.fetchall()]
        sale_orders = self.env['sale.order'].search([('id', 'in', ids)])
        if sale_orders:
            partners = sale_orders.mapped('partner_id')
            cptpart = 0
            to_invoice = self.env['sale.order']
            dateheureexec =False
            for partner in partners:      
                cptpart +=1                  
                partner_orders = sale_orders.filtered(lambda so: so.partner_id.id == partner.id)
                dateheure = datetime.datetime.today()                              
                to_invoice+=partner_orders
                if cptpart == 50:
                    cptpart =0
                    if not dateheureexec:
                        dateheureexec = dateheure+datetime.timedelta(minutes=2)
                    else:
                        dateheureexec = dateheureexec+datetime.timedelta(minutes=15)
                    self.env['ir.cron'].create({'name':'Fact. '+dateheure.strftime("%m/%d/%Y %H:%M:%S"), 
                                                'active':True, 
                                                'user_id':self.env.user.id, 
                                                'interval_number':1, 
                                                'interval_type':'days', 
                                                'numbercall':1, 
                                                'doall':1, 
                                                'nextcall':dateheureexec, 
                                                'model_id': model_id, 
                                                'code': 'model.di_create_invoices(('+str(to_invoice.ids).strip('[]')+'),%s)' % True , 
                                                'state':'code',
                                                'priority':0})    
                    to_invoice = self.env['sale.order']           
                
                    
            if cptpart > 0:
                if not dateheureexec:
                    dateheureexec = dateheure+datetime.timedelta(minutes=2)
                else:
                    dateheureexec = dateheureexec+datetime.timedelta(minutes=15)
                self.env['ir.cron'].create({'name':'Fact. '+dateheure.strftime("%m/%d/%Y %H:%M:%S"), 
                                            'active':True, 
                                            'user_id':self.env.user.id, 
                                            'interval_number':1, 
                                            'interval_type':'days', 
                                            'numbercall':1, 
                                            'doall':1, 
                                            'nextcall':dateheureexec, 
                                            'model_id': model_id, 
                                            'code': 'model.di_create_invoices(('+str(to_invoice.ids).strip('[]')+'),%s)' % True , 
                                            'state':'code',
                                            'priority':0})    
                to_invoice = self.env['sale.order'] 
                
                
                
        sale_orders = self.env['sale.order']                    
        query_args = {'periodicity_invoice': self.period_fact,'date_debut' : self.date_debut,'date_fin' : self.date_fin, 'ref_debut': self.ref_debut,'ref_fin':self.ref_fin}
        query = """ SELECT  so.id 
                        FROM sale_order so
                        INNER JOIN res_partner rp on rp.id = so.partner_id 
                        WHERE so.invoice_status = 'to invoice' 
                        AND di_livdt between %(date_debut)s AND %(date_fin)s                            
                        AND rp.ref is not null
                        AND rp.di_period_fact = %(periodicity_invoice)s
                        AND rp.ref between %(ref_debut)s AND %(ref_fin)s 
                        AND rp.di_regr_fact is false                       
                        order by so.partner_id
                        """

        self.env.cr.execute(query, query_args)
        ids = [r[0] for r in self.env.cr.fetchall()]
        sale_orders = self.env['sale.order'].search([('id', 'in', ids)])
        if sale_orders:
            partners = sale_orders.mapped('partner_id')
            cptpart = 0
            to_invoice = self.env['sale.order']
            
            for partner in partners:      
                cptpart +=1                  
                partner_orders = sale_orders.filtered(lambda so: so.partner_id.id == partner.id)
                dateheure = datetime.datetime.today()                
                
                to_invoice+=partner_orders
                if cptpart == 50:
                    cptpart =0
                    if not dateheureexec:
                        dateheureexec = dateheure+datetime.timedelta(minutes=2)
                    else:
                        dateheureexec = dateheureexec+datetime.timedelta(minutes=15)
                    self.env['ir.cron'].create({'name':'Fact. '+dateheure.strftime("%m/%d/%Y %H:%M:%S"), 
                                                'active':True, 
                                                'user_id':self.env.user.id, 
                                                'interval_number':1, 
                                                'interval_type':'days', 
                                                'numbercall':1, 
                                                'doall':1, 
                                                'nextcall':dateheureexec, 
                                                'model_id': model_id, 
                                                'code': 'model.di_create_invoices(('+str(to_invoice.ids).strip('[]')+'),%s)' % False , 
                                                'state':'code',
                                                'priority':0})    
                    to_invoice = self.env['sale.order']           
                
                    
            if cptpart > 0:
                if not dateheureexec:
                    dateheureexec = dateheure+datetime.timedelta(minutes=2)
                else:
                    dateheureexec = dateheureexec+datetime.timedelta(minutes=15)
                self.env['ir.cron'].create({'name':'Fact. '+dateheure.strftime("%m/%d/%Y %H:%M:%S"), 
                                            'active':True, 
                                            'user_id':self.env.user.id, 
                                            'interval_number':1, 
                                            'interval_type':'days', 
                                            'numbercall':1, 
                                            'doall':1, 
                                            'nextcall':dateheureexec, 
                                            'model_id': model_id, 
                                            'code': 'model.di_create_invoices(('+str(to_invoice.ids).strip('[]')+'),%s)' % False , 
                                            'state':'code',
                                            'priority':0})    
                to_invoice = self.env['sale.order'] 
                