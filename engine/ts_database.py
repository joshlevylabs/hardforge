"""
Thiele-Small parameter database for loudspeaker drivers.

Seed data for 50+ common drivers from popular manufacturers.
All values sourced from manufacturer datasheets.
"""

import json
import os
import uuid
from typing import Dict, List, Optional


# Seed data: real TS parameters from manufacturer datasheets
SEED_DRIVERS = [
    # --- Dayton Audio ---
    {"manufacturer": "Dayton Audio", "model": "RS180-8", "driver_type": "woofer",
     "re": 6.4, "le": 0.51, "fs": 39.0, "qms": 4.95, "qes": 0.47, "qts": 0.43,
     "vas": 20.0, "bl": 7.9, "mms": 16.5, "cms": 1.0, "rms": 0.84, "sd": 143.0,
     "xmax": 6.6, "nominal_impedance": 8, "power_rating": 60, "sensitivity": 86.5},

    {"manufacturer": "Dayton Audio", "model": "RS225-8", "driver_type": "woofer",
     "re": 6.0, "le": 0.72, "fs": 30.0, "qms": 5.23, "qes": 0.38, "qts": 0.35,
     "vas": 45.0, "bl": 9.2, "mms": 28.0, "cms": 1.0, "rms": 1.01, "sd": 220.0,
     "xmax": 7.0, "nominal_impedance": 8, "power_rating": 80, "sensitivity": 87.0},

    {"manufacturer": "Dayton Audio", "model": "RS150-8", "driver_type": "woofer",
     "re": 6.5, "le": 0.35, "fs": 52.0, "qms": 4.75, "qes": 0.55, "qts": 0.49,
     "vas": 9.8, "bl": 6.5, "mms": 9.5, "sd": 110.0,
     "xmax": 5.5, "nominal_impedance": 8, "power_rating": 40, "sensitivity": 85.5},

    {"manufacturer": "Dayton Audio", "model": "RS100-8", "driver_type": "full_range",
     "re": 6.2, "le": 0.15, "fs": 88.0, "qms": 3.25, "qes": 0.61, "qts": 0.51,
     "vas": 2.6, "bl": 4.8, "mms": 4.0, "sd": 52.0,
     "xmax": 3.5, "nominal_impedance": 8, "power_rating": 30, "sensitivity": 84.0},

    {"manufacturer": "Dayton Audio", "model": "ND25FW-4", "driver_type": "tweeter",
     "re": 3.3, "le": 0.03, "fs": 900.0, "qms": 2.50, "qes": 0.85, "qts": 0.63,
     "sd": 5.0, "nominal_impedance": 4, "power_rating": 30, "sensitivity": 90.0},

    {"manufacturer": "Dayton Audio", "model": "DC160-8", "driver_type": "woofer",
     "re": 6.1, "le": 0.45, "fs": 35.0, "qms": 5.10, "qes": 0.41, "qts": 0.38,
     "vas": 18.5, "bl": 8.1, "mms": 14.5, "sd": 132.0,
     "xmax": 8.0, "nominal_impedance": 8, "power_rating": 80, "sensitivity": 86.0},

    {"manufacturer": "Dayton Audio", "model": "RSS315HF-4", "driver_type": "subwoofer",
     "re": 3.5, "le": 1.8, "fs": 22.0, "qms": 6.50, "qes": 0.42, "qts": 0.39,
     "vas": 150.0, "bl": 14.5, "mms": 85.0, "sd": 470.0,
     "xmax": 16.0, "nominal_impedance": 4, "power_rating": 250, "sensitivity": 88.0},

    {"manufacturer": "Dayton Audio", "model": "DMA105-8", "driver_type": "full_range",
     "re": 6.4, "le": 0.12, "fs": 75.0, "qms": 3.80, "qes": 0.75, "qts": 0.63,
     "vas": 3.2, "bl": 4.3, "mms": 3.5, "sd": 55.0,
     "xmax": 3.0, "nominal_impedance": 8, "power_rating": 25, "sensitivity": 83.0},

    # --- SB Acoustics ---
    {"manufacturer": "SB Acoustics", "model": "SB17NRXC35-8", "driver_type": "woofer",
     "re": 5.7, "le": 0.32, "fs": 38.0, "qms": 3.60, "qes": 0.38, "qts": 0.34,
     "vas": 18.5, "bl": 7.0, "mms": 12.0, "sd": 136.0,
     "xmax": 6.0, "nominal_impedance": 8, "power_rating": 60, "sensitivity": 87.0},

    {"manufacturer": "SB Acoustics", "model": "SB23NRXS45-8", "driver_type": "woofer",
     "re": 5.8, "le": 0.55, "fs": 26.0, "qms": 4.10, "qes": 0.32, "qts": 0.30,
     "vas": 62.0, "bl": 10.0, "mms": 30.0, "sd": 250.0,
     "xmax": 9.0, "nominal_impedance": 8, "power_rating": 100, "sensitivity": 88.0},

    {"manufacturer": "SB Acoustics", "model": "SB29RDNC-C000-4", "driver_type": "tweeter",
     "re": 3.0, "le": 0.02, "fs": 500.0, "qms": 2.80, "qes": 0.70, "qts": 0.56,
     "sd": 7.0, "nominal_impedance": 4, "power_rating": 80, "sensitivity": 92.0},

    {"manufacturer": "SB Acoustics", "model": "SB12NRXS25-8", "driver_type": "midrange",
     "re": 6.0, "le": 0.08, "fs": 80.0, "qms": 3.20, "qes": 0.50, "qts": 0.43,
     "vas": 2.8, "bl": 5.2, "mms": 4.5, "sd": 52.0,
     "xmax": 4.0, "nominal_impedance": 8, "power_rating": 30, "sensitivity": 84.5},

    # --- Seas ---
    {"manufacturer": "Seas", "model": "L18RNX/P (H1480)", "driver_type": "woofer",
     "re": 5.6, "le": 0.42, "fs": 35.0, "qms": 4.20, "qes": 0.36, "qts": 0.33,
     "vas": 24.0, "bl": 8.5, "mms": 18.0, "sd": 154.0,
     "xmax": 6.0, "nominal_impedance": 8, "power_rating": 80, "sensitivity": 87.5},

    {"manufacturer": "Seas", "model": "W18NX-001 (H1215)", "driver_type": "woofer",
     "re": 5.5, "le": 0.38, "fs": 30.0, "qms": 3.80, "qes": 0.33, "qts": 0.30,
     "vas": 30.0, "bl": 9.0, "mms": 22.0, "sd": 154.0,
     "xmax": 7.0, "nominal_impedance": 8, "power_rating": 80, "sensitivity": 88.0},

    {"manufacturer": "Seas", "model": "27TDFC (H1189)", "driver_type": "tweeter",
     "re": 5.0, "le": 0.05, "fs": 550.0, "qms": 3.00, "qes": 0.65, "qts": 0.53,
     "sd": 8.5, "nominal_impedance": 6, "power_rating": 120, "sensitivity": 92.0},

    {"manufacturer": "Seas", "model": "T29MF001 (H1396)", "driver_type": "tweeter",
     "re": 5.2, "le": 0.03, "fs": 450.0, "qms": 2.50, "qes": 0.55, "qts": 0.45,
     "sd": 10.0, "nominal_impedance": 6, "power_rating": 150, "sensitivity": 93.0},

    # --- Peerless by Tymphany ---
    {"manufacturer": "Peerless", "model": "SLS-P830946 (12\")", "driver_type": "subwoofer",
     "re": 3.3, "le": 1.5, "fs": 19.0, "qms": 8.50, "qes": 0.45, "qts": 0.43,
     "vas": 200.0, "bl": 13.0, "mms": 120.0, "sd": 520.0,
     "xmax": 18.0, "nominal_impedance": 4, "power_rating": 300, "sensitivity": 87.0},

    {"manufacturer": "Peerless", "model": "830883 (HDS PPB)", "driver_type": "woofer",
     "re": 5.7, "le": 0.45, "fs": 31.0, "qms": 4.60, "qes": 0.40, "qts": 0.37,
     "vas": 32.0, "bl": 8.0, "mms": 20.0, "sd": 170.0,
     "xmax": 6.5, "nominal_impedance": 8, "power_rating": 60, "sensitivity": 87.0},

    {"manufacturer": "Peerless", "model": "XT25SC90-04", "driver_type": "tweeter",
     "re": 3.1, "le": 0.02, "fs": 700.0, "qms": 2.20, "qes": 0.80, "qts": 0.59,
     "sd": 6.0, "nominal_impedance": 4, "power_rating": 50, "sensitivity": 89.0},

    # --- Scanspeak ---
    {"manufacturer": "Scanspeak", "model": "18W/8531G00", "driver_type": "woofer",
     "re": 5.5, "le": 0.30, "fs": 37.0, "qms": 3.50, "qes": 0.35, "qts": 0.32,
     "vas": 20.0, "bl": 7.5, "mms": 14.0, "sd": 136.0,
     "xmax": 6.5, "nominal_impedance": 8, "power_rating": 60, "sensitivity": 87.5},

    {"manufacturer": "Scanspeak", "model": "22W/8534G00", "driver_type": "woofer",
     "re": 5.4, "le": 0.50, "fs": 25.0, "qms": 4.50, "qes": 0.30, "qts": 0.28,
     "vas": 55.0, "bl": 10.5, "mms": 32.0, "sd": 230.0,
     "xmax": 9.0, "nominal_impedance": 8, "power_rating": 100, "sensitivity": 89.0},

    {"manufacturer": "Scanspeak", "model": "D3004/602000 (Beryllium)", "driver_type": "tweeter",
     "re": 5.0, "le": 0.02, "fs": 500.0, "qms": 3.50, "qes": 0.55, "qts": 0.47,
     "sd": 7.0, "nominal_impedance": 6, "power_rating": 80, "sensitivity": 93.0},

    {"manufacturer": "Scanspeak", "model": "D2604/833000 (Illuminator)", "driver_type": "tweeter",
     "re": 5.0, "le": 0.03, "fs": 550.0, "qms": 2.80, "qes": 0.60, "qts": 0.49,
     "sd": 7.5, "nominal_impedance": 6, "power_rating": 100, "sensitivity": 91.5},

    {"manufacturer": "Scanspeak", "model": "15W/8531K00", "driver_type": "midrange",
     "re": 5.5, "le": 0.12, "fs": 55.0, "qms": 3.50, "qes": 0.42, "qts": 0.37,
     "vas": 8.5, "bl": 6.0, "mms": 7.5, "sd": 88.0,
     "xmax": 4.5, "nominal_impedance": 8, "power_rating": 40, "sensitivity": 86.5},

    # --- Tang Band ---
    {"manufacturer": "Tang Band", "model": "W5-1138SMF", "driver_type": "full_range",
     "re": 6.3, "le": 0.25, "fs": 62.0, "qms": 3.80, "qes": 0.65, "qts": 0.56,
     "vas": 5.5, "bl": 5.0, "mms": 5.5, "sd": 80.0,
     "xmax": 4.0, "nominal_impedance": 8, "power_rating": 20, "sensitivity": 85.0},

    {"manufacturer": "Tang Band", "model": "W6-1139SI", "driver_type": "woofer",
     "re": 5.8, "le": 0.40, "fs": 40.0, "qms": 4.50, "qes": 0.45, "qts": 0.41,
     "vas": 15.0, "bl": 7.0, "mms": 12.0, "sd": 120.0,
     "xmax": 5.5, "nominal_impedance": 8, "power_rating": 40, "sensitivity": 86.0},

    {"manufacturer": "Tang Band", "model": "W8-1772", "driver_type": "subwoofer",
     "re": 5.8, "le": 1.2, "fs": 30.0, "qms": 5.50, "qes": 0.55, "qts": 0.50,
     "vas": 60.0, "bl": 9.5, "mms": 35.0, "sd": 220.0,
     "xmax": 10.0, "nominal_impedance": 8, "power_rating": 100, "sensitivity": 86.5},

    # --- HiVi/Swans ---
    {"manufacturer": "HiVi", "model": "B4N", "driver_type": "full_range",
     "re": 6.4, "le": 0.10, "fs": 82.0, "qms": 3.20, "qes": 0.70, "qts": 0.57,
     "vas": 3.5, "bl": 4.5, "mms": 3.8, "sd": 52.0,
     "xmax": 3.0, "nominal_impedance": 8, "power_rating": 15, "sensitivity": 83.5},

    {"manufacturer": "HiVi", "model": "F6", "driver_type": "midrange",
     "re": 5.5, "le": 0.20, "fs": 48.0, "qms": 4.00, "qes": 0.40, "qts": 0.36,
     "vas": 12.0, "bl": 6.5, "mms": 10.0, "sd": 110.0,
     "xmax": 5.0, "nominal_impedance": 8, "power_rating": 40, "sensitivity": 87.0},

    {"manufacturer": "HiVi", "model": "RT1.3WE", "driver_type": "tweeter",
     "re": 5.5, "le": 0.01, "fs": 1200.0, "qms": 3.00, "qes": 1.20, "qts": 0.86,
     "sd": 4.0, "nominal_impedance": 8, "power_rating": 15, "sensitivity": 92.0},

    # --- Fountek ---
    {"manufacturer": "Fountek", "model": "FR89EX", "driver_type": "full_range",
     "re": 6.0, "le": 0.05, "fs": 110.0, "qms": 2.80, "qes": 0.72, "qts": 0.57,
     "vas": 1.5, "bl": 4.0, "mms": 2.0, "sd": 33.0,
     "xmax": 2.5, "nominal_impedance": 8, "power_rating": 15, "sensitivity": 84.0},

    {"manufacturer": "Fountek", "model": "FW168", "driver_type": "woofer",
     "re": 6.2, "le": 0.45, "fs": 38.0, "qms": 4.20, "qes": 0.42, "qts": 0.38,
     "vas": 18.0, "bl": 7.5, "mms": 15.0, "sd": 140.0,
     "xmax": 5.5, "nominal_impedance": 8, "power_rating": 50, "sensitivity": 86.5},

    # --- Vifa/Tymphany ---
    {"manufacturer": "Vifa", "model": "NE19VTS-04", "driver_type": "tweeter",
     "re": 3.2, "le": 0.02, "fs": 800.0, "qms": 2.50, "qes": 0.90, "qts": 0.66,
     "sd": 5.5, "nominal_impedance": 4, "power_rating": 30, "sensitivity": 89.0},

    {"manufacturer": "Vifa", "model": "NE149W-08", "driver_type": "woofer",
     "re": 5.8, "le": 0.38, "fs": 44.0, "qms": 4.50, "qes": 0.48, "qts": 0.43,
     "vas": 12.0, "bl": 6.8, "mms": 10.5, "sd": 107.0,
     "xmax": 5.0, "nominal_impedance": 8, "power_rating": 40, "sensitivity": 86.0},

    # --- Wavecor ---
    {"manufacturer": "Wavecor", "model": "WF182BD03", "driver_type": "woofer",
     "re": 6.0, "le": 0.35, "fs": 36.0, "qms": 3.80, "qes": 0.36, "qts": 0.33,
     "vas": 22.0, "bl": 8.0, "mms": 16.0, "sd": 154.0,
     "xmax": 6.5, "nominal_impedance": 8, "power_rating": 60, "sensitivity": 87.0},

    {"manufacturer": "Wavecor", "model": "TW030WA12", "driver_type": "tweeter",
     "re": 5.5, "le": 0.02, "fs": 600.0, "qms": 2.90, "qes": 0.70, "qts": 0.56,
     "sd": 7.0, "nominal_impedance": 6, "power_rating": 50, "sensitivity": 90.5},

    # --- Morel ---
    {"manufacturer": "Morel", "model": "CAT 378", "driver_type": "tweeter",
     "re": 5.0, "le": 0.02, "fs": 450.0, "qms": 3.00, "qes": 0.50, "qts": 0.43,
     "sd": 10.0, "nominal_impedance": 6, "power_rating": 100, "sensitivity": 91.0},

    {"manufacturer": "Morel", "model": "TiCW 634", "driver_type": "woofer",
     "re": 5.3, "le": 0.50, "fs": 28.0, "qms": 4.50, "qes": 0.35, "qts": 0.32,
     "vas": 40.0, "bl": 9.5, "mms": 25.0, "sd": 200.0,
     "xmax": 8.0, "nominal_impedance": 8, "power_rating": 100, "sensitivity": 88.0},

    # --- SICA ---
    {"manufacturer": "SICA", "model": "Z002610", "driver_type": "midrange",
     "re": 5.0, "le": 0.15, "fs": 60.0, "qms": 4.00, "qes": 0.50, "qts": 0.44,
     "vas": 5.0, "bl": 5.5, "mms": 6.0, "sd": 75.0,
     "xmax": 3.5, "nominal_impedance": 8, "power_rating": 30, "sensitivity": 86.0},

    # --- Aura Sound ---
    {"manufacturer": "Aura Sound", "model": "NS3-193-8A", "driver_type": "full_range",
     "re": 6.5, "le": 0.08, "fs": 120.0, "qms": 3.00, "qes": 0.80, "qts": 0.63,
     "vas": 0.8, "bl": 3.5, "mms": 1.5, "sd": 23.0,
     "xmax": 2.0, "nominal_impedance": 8, "power_rating": 10, "sensitivity": 81.0},

    # --- Eminence ---
    {"manufacturer": "Eminence", "model": "Alpha-6A", "driver_type": "woofer",
     "re": 5.2, "le": 0.60, "fs": 75.0, "qms": 7.50, "qes": 0.68, "qts": 0.62,
     "vas": 10.0, "bl": 6.0, "mms": 9.0, "sd": 132.0,
     "xmax": 3.0, "nominal_impedance": 8, "power_rating": 100, "sensitivity": 90.5},

    {"manufacturer": "Eminence", "model": "Kappa Pro-15A", "driver_type": "subwoofer",
     "re": 5.3, "le": 1.8, "fs": 38.0, "qms": 9.00, "qes": 0.35, "qts": 0.34,
     "vas": 185.0, "bl": 18.0, "mms": 95.0, "sd": 855.0,
     "xmax": 5.0, "nominal_impedance": 8, "power_rating": 500, "sensitivity": 97.0},

    # --- Audax ---
    {"manufacturer": "Audax", "model": "HM170Z18", "driver_type": "woofer",
     "re": 5.5, "le": 0.40, "fs": 40.0, "qms": 4.00, "qes": 0.42, "qts": 0.38,
     "vas": 16.0, "bl": 7.2, "mms": 13.0, "sd": 132.0,
     "xmax": 5.0, "nominal_impedance": 8, "power_rating": 50, "sensitivity": 86.5},

    # --- Parts Express (Buyout/GRS) ---
    {"manufacturer": "GRS", "model": "8FR-8", "driver_type": "full_range",
     "re": 6.5, "le": 0.20, "fs": 55.0, "qms": 5.00, "qes": 0.80, "qts": 0.69,
     "vas": 18.0, "bl": 5.5, "mms": 8.0, "sd": 132.0,
     "xmax": 3.0, "nominal_impedance": 8, "power_rating": 25, "sensitivity": 87.0},

    # --- Faital Pro ---
    {"manufacturer": "Faital Pro", "model": "6FE200", "driver_type": "woofer",
     "re": 5.2, "le": 0.60, "fs": 60.0, "qms": 6.50, "qes": 0.50, "qts": 0.46,
     "vas": 9.5, "bl": 7.0, "mms": 10.0, "sd": 132.0,
     "xmax": 4.0, "nominal_impedance": 8, "power_rating": 130, "sensitivity": 91.5},

    {"manufacturer": "Faital Pro", "model": "HF10AK", "driver_type": "tweeter",
     "re": 5.5, "le": 0.01, "fs": 800.0, "qms": 3.50, "qes": 0.80, "qts": 0.65,
     "sd": 8.0, "nominal_impedance": 8, "power_rating": 40, "sensitivity": 105.0},

    # --- Celestion ---
    {"manufacturer": "Celestion", "model": "TF1225", "driver_type": "woofer",
     "re": 5.4, "le": 0.80, "fs": 45.0, "qms": 8.00, "qes": 0.42, "qts": 0.40,
     "vas": 110.0, "bl": 11.0, "mms": 45.0, "sd": 470.0,
     "xmax": 5.0, "nominal_impedance": 8, "power_rating": 250, "sensitivity": 95.0},

    # --- Beyma ---
    {"manufacturer": "Beyma", "model": "8AG/N", "driver_type": "woofer",
     "re": 5.5, "le": 0.70, "fs": 55.0, "qms": 7.00, "qes": 0.50, "qts": 0.47,
     "vas": 25.0, "bl": 8.0, "mms": 15.0, "sd": 220.0,
     "xmax": 4.0, "nominal_impedance": 8, "power_rating": 100, "sensitivity": 92.0},

    # --- Accuton ---
    {"manufacturer": "Accuton", "model": "C173-6-096E", "driver_type": "midrange",
     "re": 4.5, "le": 0.05, "fs": 60.0, "qms": 3.00, "qes": 0.50, "qts": 0.43,
     "vas": 5.0, "bl": 6.0, "mms": 6.0, "sd": 100.0,
     "xmax": 3.0, "nominal_impedance": 6, "power_rating": 50, "sensitivity": 87.0},

    # --- More Dayton budget options ---
    {"manufacturer": "Dayton Audio", "model": "DS175-8", "driver_type": "woofer",
     "re": 6.5, "le": 0.55, "fs": 42.0, "qms": 6.50, "qes": 0.55, "qts": 0.51,
     "vas": 15.0, "bl": 6.5, "mms": 12.0, "sd": 132.0,
     "xmax": 5.0, "nominal_impedance": 8, "power_rating": 35, "sensitivity": 85.0},

    {"manufacturer": "Dayton Audio", "model": "TCP115-8", "driver_type": "woofer",
     "re": 6.0, "le": 0.40, "fs": 50.0, "qms": 5.50, "qes": 0.60, "qts": 0.54,
     "vas": 7.0, "bl": 5.5, "mms": 8.0, "sd": 80.0,
     "xmax": 4.5, "nominal_impedance": 8, "power_rating": 30, "sensitivity": 83.5},
]


class DriverDatabase:
    """In-memory driver database with search capabilities."""

    def __init__(self, seed: bool = True):
        self.drivers: List[Dict] = []
        if seed:
            self._load_seed_data()

    def _load_seed_data(self):
        """Load seed driver data and assign IDs."""
        for i, driver in enumerate(SEED_DRIVERS):
            d = dict(driver)
            d['id'] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{d['manufacturer']}:{d['model']}"))
            self.drivers.append(d)

    def search(
        self,
        query: Optional[str] = None,
        manufacturer: Optional[str] = None,
        driver_type: Optional[str] = None,
    ) -> List[Dict]:
        """Search drivers by text query, manufacturer, or type."""
        results = self.drivers

        if manufacturer:
            results = [d for d in results if d['manufacturer'].lower() == manufacturer.lower()]

        if driver_type:
            results = [d for d in results if d.get('driver_type', '') == driver_type]

        if query:
            q = query.lower()
            results = [
                d for d in results
                if q in d['manufacturer'].lower()
                or q in d['model'].lower()
                or q in d.get('driver_type', '').lower()
            ]

        return results

    def get_by_id(self, driver_id: str) -> Optional[Dict]:
        """Get a driver by its ID."""
        for d in self.drivers:
            if d.get('id') == driver_id:
                return d
        return None

    def get_by_model(self, manufacturer: str, model: str) -> Optional[Dict]:
        """Get a driver by manufacturer and model name."""
        for d in self.drivers:
            if (d['manufacturer'].lower() == manufacturer.lower()
                    and d['model'].lower() == model.lower()):
                return d
        return None

    def add_driver(self, driver: Dict) -> Dict:
        """Add a new driver to the database."""
        d = dict(driver)
        if 'id' not in d:
            d['id'] = str(uuid.uuid4())
        self.drivers.append(d)
        return d

    def export_json(self) -> str:
        """Export all drivers as JSON."""
        return json.dumps(self.drivers, indent=2)

    def import_json(self, json_str: str):
        """Import drivers from JSON string."""
        data = json.loads(json_str)
        for d in data:
            if 'id' not in d:
                d['id'] = str(uuid.uuid4())
            self.drivers.append(d)

    @property
    def manufacturers(self) -> List[str]:
        """Get list of unique manufacturers."""
        return sorted(set(d['manufacturer'] for d in self.drivers))

    @property
    def count(self) -> int:
        return len(self.drivers)


# Module-level convenience functions
_default_db = None


def _get_db() -> DriverDatabase:
    global _default_db
    if _default_db is None:
        _default_db = DriverDatabase()
    return _default_db


def search_drivers(query: Optional[str] = None, **kwargs) -> List[Dict]:
    return _get_db().search(query=query, **kwargs)


def get_driver(manufacturer: str, model: str) -> Optional[Dict]:
    return _get_db().get_by_model(manufacturer, model)
