"""
Shared enumerations for the export and logistics domain.
Defining them once avoids duplicate SQLAlchemy DB enum type names.
"""
import enum


class HerbGrade(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    premium = "premium"


class PackagingType(str, enum.Enum):
    bulk_bag = "bulk_bag"
    vacuum_sealed = "vacuum_sealed"
    drum = "drum"
    carton = "carton"


class FreightChannel(str, enum.Enum):
    air = "air"
    sea = "sea"
    road = "road"
    ecommerce = "ecommerce"


class Incoterms(str, enum.Enum):
    FOB = "FOB"
    CIF = "CIF"
    EXW = "EXW"
    DDP = "DDP"
    DAP = "DAP"


class PaymentMethod(str, enum.Enum):
    paystack = "paystack"
    flutterwave = "flutterwave"
    stripe = "stripe"
    paypal = "paypal"
    swift = "swift"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    escrow_held = "escrow_held"
    released = "released"
    refunded = "refunded"


class OrderStatus(str, enum.Enum):
    placed = "placed"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    in_transit = "in_transit"
    cleared_customs = "cleared_customs"
    delivered = "delivered"
    disputed = "disputed"


class ShipmentEventType(str, enum.Enum):
    departure = "departure"
    arrival = "arrival"
    customs_hold = "customs_hold"
    delay = "delay"
    customs_cleared = "customs_cleared"
    delivered = "delivered"
    temperature_breach = "temperature_breach"


class ExportDocType(str, enum.Enum):
    commercial_invoice = "commercial_invoice"
    packing_list = "packing_list"
    bill_of_lading = "bill_of_lading"
    airway_bill = "airway_bill"
    certificate_of_origin = "certificate_of_origin"
    phytosanitary_certificate = "phytosanitary_certificate"
    nafdac_export_cert = "nafdac_export_cert"
    nepc_certificate = "nepc_certificate"
    customs_declaration = "customs_declaration"


class BuyerType(str, enum.Enum):
    pharma_company = "pharma_company"
    herbal_retailer = "herbal_retailer"
    cosmetics_brand = "cosmetics_brand"
    research_institution = "research_institution"
    distributor = "distributor"
    individual = "individual"


class MarketRegion(str, enum.Enum):
    europe = "europe"
    north_america = "north_america"
    asia = "asia"
    middle_east = "middle_east"
    africa = "africa"


class EscrowStatus(str, enum.Enum):
    held = "held"
    released = "released"
    refunded = "refunded"
    disputed = "disputed"
