from __future__ import annotations

from sqladmin import ModelView

from models.catalog import Country, OSOption, Plan, USState, Validity
from models.config import MessageTemplate, Setting
from models.order import Delivery, Order, Payment
from models.telegram import TelegramUser, UserState
from models.webhook import WebhookEvent


class CountryAdmin(ModelView, model=Country):
    name = "Country"
    name_plural = "Countries"
    icon = "fa-solid fa-globe"
    category = "Catalog"
    column_list = [Country.id, Country.name, Country.prefix, Country.is_active, Country.sort_order]
    column_sortable_list = [Country.sort_order, Country.name]
    column_searchable_list = [Country.name, Country.prefix]
    form_columns = [Country.name, Country.prefix, Country.is_active, Country.sort_order]


class USStateAdmin(ModelView, model=USState):
    name = "US State"
    name_plural = "US States"
    icon = "fa-solid fa-map"
    category = "Catalog"
    column_list = [USState.id, USState.name, USState.country_id, USState.is_active, USState.sort_order]
    column_sortable_list = [USState.sort_order, USState.name]
    column_searchable_list = [USState.name]
    form_columns = [USState.country_id, USState.name, USState.is_active, USState.sort_order]


class PlanAdmin(ModelView, model=Plan):
    name = "Plan"
    name_plural = "Plans"
    icon = "fa-solid fa-box"
    category = "Catalog"
    column_list = [
        Plan.id, Plan.name, Plan.ram_gb, Plan.cpu_cores,
        Plan.ssd_gb, Plan.price_usd, Plan.is_active, Plan.sort_order,
    ]
    column_sortable_list = [Plan.sort_order, Plan.price_usd]
    column_searchable_list = [Plan.name]
    form_columns = [
        Plan.name, Plan.ram_gb, Plan.cpu_cores, Plan.ssd_gb,
        Plan.price_usd, Plan.is_active, Plan.sort_order,
    ]


class OSOptionAdmin(ModelView, model=OSOption):
    name = "OS Option"
    name_plural = "OS Options"
    icon = "fa-solid fa-desktop"
    category = "Catalog"
    column_list = [OSOption.id, OSOption.name, OSOption.is_active, OSOption.sort_order]
    column_sortable_list = [OSOption.sort_order]
    column_searchable_list = [OSOption.name]
    form_columns = [OSOption.name, OSOption.is_active, OSOption.sort_order]


class ValidityAdmin(ModelView, model=Validity):
    name = "Validity"
    name_plural = "Validities"
    icon = "fa-solid fa-calendar"
    category = "Catalog"
    column_list = [Validity.id, Validity.label, Validity.days, Validity.is_active]
    form_columns = [Validity.label, Validity.days, Validity.is_active]


class OrderAdmin(ModelView, model=Order):
    name = "Order"
    name_plural = "Orders"
    icon = "fa-solid fa-shopping-cart"
    category = "Orders"
    column_list = [
        Order.id, Order.telegram_user_id, Order.country_id,
        Order.plan_id, Order.customer_email, Order.status,
        Order.created_at, Order.updated_at,
    ]
    column_sortable_list = [Order.created_at, Order.status]
    column_searchable_list = [Order.customer_email]
    column_filters = [Order.status]
    can_create = False
    can_delete = False
    form_columns = [Order.status, Order.customer_email]


class PaymentAdmin(ModelView, model=Payment):
    name = "Payment"
    name_plural = "Payments"
    icon = "fa-solid fa-credit-card"
    category = "Orders"
    column_list = [
        Payment.id, Payment.order_id, Payment.amount_usd,
        Payment.status, Payment.expires_at, Payment.paid_at, Payment.created_at,
    ]
    column_sortable_list = [Payment.created_at, Payment.status]
    can_create = False
    can_delete = False
    form_columns = [Payment.status, Payment.paid_at]


class DeliveryAdmin(ModelView, model=Delivery):
    name = "Delivery"
    name_plural = "Deliveries"
    icon = "fa-solid fa-server"
    category = "Orders"
    column_list = [
        Delivery.id, Delivery.order_id, Delivery.ip_address,
        Delivery.username, Delivery.expiry_date, Delivery.delivered_at,
    ]
    column_sortable_list = [Delivery.delivered_at]
    form_columns = [
        Delivery.order_id, Delivery.ip_address, Delivery.username,
        Delivery.password, Delivery.expiry_date,
    ]


class SettingAdmin(ModelView, model=Setting):
    name = "Setting"
    name_plural = "Settings"
    icon = "fa-solid fa-gear"
    category = "Config"
    column_list = [Setting.id, Setting.key, Setting.value, Setting.description]
    column_searchable_list = [Setting.key]
    form_columns = [Setting.key, Setting.value, Setting.description]


class MessageTemplateAdmin(ModelView, model=MessageTemplate):
    name = "Message Template"
    name_plural = "Message Templates"
    icon = "fa-solid fa-envelope"
    category = "Config"
    column_list = [MessageTemplate.id, MessageTemplate.slug, MessageTemplate.name]
    column_searchable_list = [MessageTemplate.slug, MessageTemplate.name]
    form_columns = [MessageTemplate.slug, MessageTemplate.name, MessageTemplate.body_text]


class TelegramUserAdmin(ModelView, model=TelegramUser):
    name = "Telegram User"
    name_plural = "Telegram Users"
    icon = "fa-solid fa-user"
    category = "Config"
    column_list = [
        TelegramUser.id, TelegramUser.telegram_id,
        TelegramUser.first_name, TelegramUser.username, TelegramUser.created_at,
    ]
    column_searchable_list = [TelegramUser.username, TelegramUser.telegram_id]
    can_create = False
    can_delete = False
    form_columns = [TelegramUser.first_name, TelegramUser.last_name, TelegramUser.username]


class WebhookEventAdmin(ModelView, model=WebhookEvent):
    name = "Webhook Event"
    name_plural = "Webhook Events"
    icon = "fa-solid fa-webhook"
    category = "Logs"
    column_list = [
        WebhookEvent.id, WebhookEvent.source, WebhookEvent.event_type,
        WebhookEvent.processed, WebhookEvent.error_message, WebhookEvent.created_at,
    ]
    column_sortable_list = [WebhookEvent.created_at]
    column_filters = [WebhookEvent.source, WebhookEvent.processed]
    can_create = False
    can_edit = False
    can_delete = False
