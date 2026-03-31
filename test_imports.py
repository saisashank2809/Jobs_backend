try:
    from app.scraper.deloitte_adapter import DeloitteAdapter
    print("DeloitteAdapter loaded")
except ImportError as e:
    print(f"DeloitteAdapter failed: {e}")

try:
    from app.scraper.pwc_adapter import PwCAdapter
    print("PwCAdapter loaded")
except ImportError as e:
    print(f"PwCAdapter failed: {e}")

try:
    from app.scraper.kpmg_adapter import KPMGAdapter
    print("KPMGAdapter loaded")
except ImportError as e:
    print(f"KPMGAdapter failed: {e}")

try:
    from app.scraper.ey_adapter import EYAdapter
    print("EYAdapter loaded")
except ImportError as e:
    print(f"EYAdapter failed: {e}")

try:
    from app.scraper.generic_adapter import GenericAdapter
    print("GenericAdapter loaded")
except ImportError as e:
    print(f"GenericAdapter failed: {e}")
