"""
Management command: fill name_en for SealCategory (top-level categories that have Russian names).
Subcategories with codes (like K21, BRW01) don't need translation — the code is already in English.
Also fills org_legal_en and address_en in SiteSettings if they are at default values.
"""
from django.core.management.base import BaseCommand
from apps.core.models import SealCategory, SiteSettings

CATEGORY_TRANSLATIONS = {
    # slug → name_en
    "amortizatori_dlya_elektroprivodov_nasosov": "Couplings / Pump Drive Buffers",
    "krpms-vorotnikovye": "Collar Seals",
    "krpms-vorotnikovye-manzhety": "Collar Seals",
    "gidravlicheskie": "Hydraulic Seals",
    "grjazesemniki": "Wiper Seals / Scrapers",
    "quers-a-seals": "Wiper Seals (QUERS)",
    "krpms-gryazesemniki": "Wiper Seals (KRPMS)",
    "koltsa_obzhimnie_usit": "USIT Rings (Crimping)",
    "koltsa_zashchitnye": "Protection Rings",
    "koltsa_stopornye": "Retaining Rings",
    "kolca_uplatnitelnye": "Sealing Rings / O-Rings",
    "krpms-komplekty-uplotneniy": "Hydraulic Cylinder Seal Kits",
    "manzhety": "BKh Seals",
    "manzhety_armirovannye": "Reinforced / Shaft Seals (Lip Seals)",
    "manzhety_gidravlicheskie": "Universal Hydraulic Seals",
    "krpms-manzhety-uplotnitelnye": "Sealing Seals (KRPMS)",
    "krpms-napravlyayuschie": "Guide Rings (KRPMS)",
    "napravljajuwie_gidrocilindrov": "Guide Rings / Bearing Rings",
    "quers-f-seals": "Guide Rings (QUERS)",
    "krpms-o-koltca": "O-Rings (KRPMS)",
    "o-kolca": "O-Rings USIT",
    "krpms-napravlyayushhie-kolca-dlya-gidrocilindrov": "Support / Guide Rings",
    "krpms-porshnevye": "Piston Seals (KRPMS)",
    "krpms-uplotnitelnye-kolcza": "Sealing Rings (KRPMS)",
    "krpms-uplotneniya-bolshogo-diametra": "Large Diameter Seals",
    "krpms-uplotneniya": "Hydraulic Cylinder Seals (KRPMS)",
    "krpms-uplotneniya-dlya-gornoy-promyshlennosti": "Mining Industry Seals",
    "krpms-uplotneniya-dlya-gornoy": "Mining Industry Seals",
    "quers-k-seals": "Piston Seals (QUERS)",
    "quers-r-seals": "Rotary Seals (QUERS)",
    "quers-s-seals": "Rod / Shaft Seals (QUERS)",
    "uplotnenija_porshnja": "Piston Seals",
    "krpms-uplotneniya-porshnya": "Piston Seals (KRPMS)",
    "uplotnenija_shtoka": "Rod Seals",
    "krpms-uplotneniya-shtoka": "Rod Seals (KRPMS)",
    "quers-seals-rings": "Sealing Rings (QUERS)",
    "krpms-kruglogo-secheniya": "Round Cross-Section Rings",
    "shaiba": "Copper Washers / Sealing Washers",
    "krpms-manzheta-shevronnaya": "Chevron Seals (KRPMS)",
    "manzheti_shevronnie": "Chevron Seals",
    "v-ring": "V-Rings",
}

# Subcategory translations (for those with Russian names as children)
SUBCATEGORY_TRANSLATIONS = {
    "koltsa_zashchitnye-dlya_manzhet": "For Seals",
    "koltsa_stopornye-vnutrennie": "Internal",
    "koltsa_stopornye-gost_13942_86": "GOST 13942-86",
    "koltsa_stopornye-naruzhnye": "External",
    "manzhety_armirovannye-epdm": "EPDM",
    "manzhety_armirovannye-fkm": "FKM",
    "manzhety_armirovannye-sil": "Silicone",
    "krpms-manzhety-uplotnitelnye-dlya-gidroczilindrov": "Seals for Hydraulic Cylinders",
    "shaiba-nabory": "Sets / Assortments",
    "krpms-uplotnitelnye-kolcza-kvadratnogo-secheniya": "Square Cross-Section Rings",
    "krpms-uplotnitelnye-kolcza-pryamougolnogo-secheniya": "Rectangular Cross-Section Rings",
}


class Command(BaseCommand):
    help = "Fill name_en for SealCategory (top-level Russian names)"

    def handle(self, *args, **options):
        updated = 0
        skipped = 0

        all_cats = SealCategory.objects.all()
        for cat in all_cats:
            en = CATEGORY_TRANSLATIONS.get(cat.slug) or SUBCATEGORY_TRANSLATIONS.get(cat.slug)
            if en:
                cat.name_en = en
                cat.save(update_fields=["name_en"])
                updated += 1
            else:
                skipped += 1

        # Make sure SiteSettings has en fields populated
        s = SiteSettings.load()
        changed = False
        if not s.org_legal_en:
            s.org_legal_en = "IE Tumanov Ivan Sergeyevich"
            changed = True
        if not s.address_en:
            s.address_en = "Artseulovsky alley 15"
            changed = True
        if changed:
            s.save()
            self.stdout.write("SiteSettings en fields updated.")
        else:
            self.stdout.write("SiteSettings en fields already filled.")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {updated} categories updated with name_en, {skipped} skipped (no translation defined or already has code)."
            )
        )
