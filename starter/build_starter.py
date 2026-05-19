"""Generate the top-~100 US electric utilities starter list.

Outputs:
  starter/top_utilities.csv          - human-readable, sorted by customers
  starter/registry_starter.json     - drop-in registry.json (all enabled:false)

IMPORTANT - read before trusting this:
  * customers_k is APPROXIMATE (thousands), used only to ORDER the list.
    Operating-utility customer counts shift yearly; treat as a priority guide.
  * platform_guess is a STARTING HYPOTHESIS. KUBRA is the most common US
    outage-map vendor, so unknown large IOUs are guessed "kubra". CONFIRM every
    one in notebook 01 with browser DevTools before enabling it.
  * outage_map_url is the public outage-map landing page (best-effort). The
    real metadata/tile or FeatureServer endpoints are NOT here - you capture
    those per-utility in notebook 01. Some URLs will have changed; verify.

Fields per utility: rank, utility_id, utility_name, parent, states,
customers_k, platform_guess, outage_map_url.
"""
import csv
import json
from pathlib import Path

OUT = Path("/home/claude/national_outage_collector/starter")
OUT.mkdir(parents=True, exist_ok=True)

# (utility_id, utility_name, parent, states, customers_k, platform_guess, outage_map_url)
UTILITIES = [
    ("PGE_CA", "Pacific Gas & Electric", "PG&E Corp", "CA", 5500, "kubra",
     "https://pgealerts.alerts.pge.com/outage-center/"),
    ("FPL", "Florida Power & Light", "NextEra Energy", "FL", 5800, "kubra",
     "https://www.fpl.com/outages/power-tracker.html"),
    ("SCE", "Southern California Edison", "Edison International", "CA", 5200, "kubra",
     "https://www.sce.com/outage-center/check-outage-status"),
    ("COMED", "Commonwealth Edison (ComEd)", "Exelon", "IL", 4100, "kubra",
     "https://www.comed.com/outages/check-outage-status"),
    ("CONED", "Consolidated Edison", "Con Edison Inc", "NY", 3600, "arcgis",
     "https://www.coned.com/en/outage-maps"),
    ("GA_POWER", "Georgia Power", "Southern Company", "GA", 2900, "kubra",
     "https://outagemap.georgiapower.com/"),
    ("DTE", "DTE Electric", "DTE Energy", "MI", 2300, "kubra",
     "https://www.newlook.dteenergy.com/wps/wcm/connect/dte-web/outage"),
    ("ONCOR", "Oncor Electric Delivery", "Sempra", "TX", 4000, "kubra",
     "https://stormcenter.oncor.com/"),
    ("DUKE_CAROLINAS", "Duke Energy Carolinas", "Duke Energy", "NC,SC", 2900, "kubra",
     "https://www.duke-energy.com/outages/current-outages"),
    ("DUKE_PROGRESS", "Duke Energy Progress", "Duke Energy", "NC,SC", 1700, "kubra",
     "https://www.duke-energy.com/outages/current-outages"),
    ("DUKE_FLORIDA", "Duke Energy Florida", "Duke Energy", "FL", 1900, "kubra",
     "https://www.duke-energy.com/outages/current-outages"),
    ("VA_POWER", "Virginia Electric Power (Dominion)", "Dominion Energy", "VA,NC", 2700, "kubra",
     "https://outagemap.dominionenergy.com/"),
    ("CENTERPOINT", "CenterPoint Energy Houston Electric", "CenterPoint Energy", "TX", 2700, "kubra",
     "https://tracker.centerpointenergy.com/"),
    ("APS", "Arizona Public Service", "Pinnacle West", "AZ", 1400, "kubra",
     "https://www.aps.com/en/Outages/Outage-Map"),
    ("PSEG", "PSE&G", "Public Service Enterprise Group", "NJ", 2300, "kubra",
     "https://outagecenter.pseg.com/"),
    ("XCEL_NORTH", "Xcel Energy (Northern States Power)", "Xcel Energy", "MN,WI,ND,SD", 1700, "kubra",
     "https://www.xcelenergy.com/outage_and_emergency/view_outage_map"),
    ("XCEL_PSCO", "Xcel Energy (Public Service Co of Colorado)", "Xcel Energy", "CO", 1500, "kubra",
     "https://www.xcelenergy.com/outage_and_emergency/view_outage_map"),
    ("AEP_OHIO", "AEP Ohio", "American Electric Power", "OH", 1500, "kubra",
     "https://www.aepohio.com/outages/map"),
    ("AEP_TEXAS", "AEP Texas", "American Electric Power", "TX", 1100, "kubra",
     "https://www.aeptexas.com/outages/map"),
    ("APCO", "Appalachian Power", "American Electric Power", "VA,WV,TN", 1000, "kubra",
     "https://www.appalachianpower.com/outages/map"),
    ("PSO", "Public Service Co of Oklahoma", "American Electric Power", "OK", 580, "kubra",
     "https://www.psoklahoma.com/outages/map"),
    ("SWEPCO", "Southwestern Electric Power", "American Electric Power", "AR,LA,TX", 540, "kubra",
     "https://www.swepco.com/outages/map"),
    ("I_AND_M", "Indiana Michigan Power", "American Electric Power", "IN,MI", 600, "kubra",
     "https://www.indianamichiganpower.com/outages/map"),
    ("KENTUCKY_POWER", "Kentucky Power", "American Electric Power", "KY", 165, "kubra",
     "https://www.kentuckypower.com/outages/map"),
    ("PECO", "PECO Energy", "Exelon", "PA", 1700, "kubra",
     "https://www.peco.com/outages/check-outage-status"),
    ("BGE", "Baltimore Gas & Electric", "Exelon", "MD", 1300, "kubra",
     "https://www.bge.com/outages/check-outage-status"),
    ("PEPCO", "Pepco", "Exelon", "DC,MD", 900, "kubra",
     "https://www.pepco.com/outages/check-outage-status"),
    ("DELMARVA", "Delmarva Power", "Exelon", "DE,MD", 530, "kubra",
     "https://www.delmarva.com/outages/check-outage-status"),
    ("ACE", "Atlantic City Electric", "Exelon", "NJ", 560, "kubra",
     "https://www.atlanticcityelectric.com/outages/check-outage-status"),
    ("PUGET", "Puget Sound Energy", "Puget Holdings", "WA", 1200, "kubra",
     "https://www.pse.com/en/outage/outage-map"),
    ("AMEREN_MO", "Ameren Missouri", "Ameren", "MO", 1200, "kubra",
     "https://outagemap.ameren.com/"),
    ("AMEREN_IL", "Ameren Illinois", "Ameren", "IL", 1200, "kubra",
     "https://outagemap.ameren.com/"),
    ("ENTERGY_AR", "Entergy Arkansas", "Entergy", "AR", 730, "kubra",
     "https://www.entergy.com/outages/"),
    ("ENTERGY_LA", "Entergy Louisiana", "Entergy", "LA", 1100, "kubra",
     "https://www.entergy.com/outages/"),
    ("ENTERGY_MS", "Entergy Mississippi", "Entergy", "MS", 460, "kubra",
     "https://www.entergy.com/outages/"),
    ("ENTERGY_TX", "Entergy Texas", "Entergy", "TX", 510, "kubra",
     "https://www.entergy.com/outages/"),
    ("ENTERGY_NO", "Entergy New Orleans", "Entergy", "LA", 210, "kubra",
     "https://www.entergy.com/outages/"),
    ("NATGRID_NY", "National Grid (New York)", "National Grid", "NY", 1700, "kubra",
     "https://www.nationalgridus.com/outages/"),
    ("NATGRID_MA", "National Grid (Massachusetts)", "National Grid", "MA", 1300, "kubra",
     "https://www.nationalgridus.com/outages/"),
    ("EVERSOURCE_MA", "Eversource (Massachusetts)", "Eversource Energy", "MA", 1500, "kubra",
     "https://outagemap.eversource.com/"),
    ("EVERSOURCE_CT", "Eversource (Connecticut)", "Eversource Energy", "CT", 1300, "kubra",
     "https://outagemap.eversource.com/"),
    ("EVERSOURCE_NH", "Eversource (New Hampshire)", "Eversource Energy", "NH", 530, "kubra",
     "https://outagemap.eversource.com/"),
    ("FE_OHIO_EDISON", "Ohio Edison", "FirstEnergy", "OH", 1100, "kubra",
     "https://www.firstenergycorp.com/outages/outage_map.html"),
    ("FE_CEI", "Cleveland Electric Illuminating", "FirstEnergy", "OH", 750, "kubra",
     "https://www.firstenergycorp.com/outages/outage_map.html"),
    ("FE_TOLEDO", "Toledo Edison", "FirstEnergy", "OH", 320, "kubra",
     "https://www.firstenergycorp.com/outages/outage_map.html"),
    ("FE_PENELEC", "Pennsylvania Electric (Penelec)", "FirstEnergy", "PA", 600, "kubra",
     "https://www.firstenergycorp.com/outages/outage_map.html"),
    ("FE_PPL_WPP", "West Penn Power", "FirstEnergy", "PA", 730, "kubra",
     "https://www.firstenergycorp.com/outages/outage_map.html"),
    ("FE_METED", "Metropolitan Edison (Met-Ed)", "FirstEnergy", "PA", 580, "kubra",
     "https://www.firstenergycorp.com/outages/outage_map.html"),
    ("FE_JCPL", "Jersey Central Power & Light", "FirstEnergy", "NJ", 1100, "kubra",
     "https://www.firstenergycorp.com/outages/outage_map.html"),
    ("FE_MON_POWER", "Mon Power", "FirstEnergy", "WV", 400, "kubra",
     "https://www.firstenergycorp.com/outages/outage_map.html"),
    ("FE_POTOMAC", "Potomac Edison", "FirstEnergy", "MD,WV", 430, "kubra",
     "https://www.firstenergycorp.com/outages/outage_map.html"),
    ("PPL_PA", "PPL Electric Utilities", "PPL Corp", "PA", 1500, "kubra",
     "https://www.pplelectric.com/outages/"),
    ("LGE", "Louisville Gas & Electric", "PPL Corp", "KY", 430, "kubra",
     "https://lge-ku.com/outages"),
    ("KU", "Kentucky Utilities", "PPL Corp", "KY,VA", 560, "kubra",
     "https://lge-ku.com/outages"),
    ("NIPSCO", "Northern Indiana Public Service (NIPSCO)", "NiSource", "IN", 480, "kubra",
     "https://www.nipsco.com/outages"),
    ("CONSUMERS", "Consumers Energy", "CMS Energy", "MI", 1900, "kubra",
     "https://www.consumersenergy.com/outage-center/outage-map"),
    ("WE_ENERGIES", "We Energies", "WEC Energy Group", "WI", 1200, "kubra",
     "https://www.we-energies.com/outages/outage-map"),
    ("ALLIANT_WI", "Alliant Energy (Wisconsin Power & Light)", "Alliant Energy", "WI", 500, "kubra",
     "https://www.alliantenergy.com/outage"),
    ("ALLIANT_IA", "Alliant Energy (Interstate Power & Light)", "Alliant Energy", "IA,MN", 500, "kubra",
     "https://www.alliantenergy.com/outage"),
    ("MIDAMERICAN", "MidAmerican Energy", "Berkshire Hathaway Energy", "IA,IL,SD,NE", 800, "kubra",
     "https://www.midamericanenergy.com/outage-map"),
    ("PACIFICORP_PP", "Pacific Power", "Berkshire Hathaway Energy", "OR,WA,CA", 780, "kubra",
     "https://www.pacificpower.net/outages-safety/outages/outage-map.html"),
    ("PACIFICORP_RMP", "Rocky Mountain Power", "Berkshire Hathaway Energy", "UT,WY,ID", 1200, "kubra",
     "https://www.rockymountainpower.net/outages-safety/outages/outage-map.html"),
    ("NV_ENERGY", "NV Energy", "Berkshire Hathaway Energy", "NV", 1300, "kubra",
     "https://www.nvenergy.com/outages/map"),
    ("PSNC_PIEDMONT", "Dominion Energy South Carolina", "Dominion Energy", "SC", 780, "kubra",
     "https://outagemap.dominionenergy.com/"),
    ("SDGE", "San Diego Gas & Electric", "Sempra", "CA", 1400, "kubra",
     "https://www.sdge.com/residential/customer-service/outage-center/outage-map"),
    ("SOCALGAS_NA", "PNM (Public Service Co of New Mexico)", "TXNM Energy", "NM", 540, "kubra",
     "https://www.pnm.com/outage-center"),
    ("EL_PASO", "El Paso Electric", "JP Morgan IIF", "TX,NM", 460, "kubra",
     "https://www.epelectric.com/outages"),
    ("TUCSON", "Tucson Electric Power", "Fortis", "AZ", 450, "kubra",
     "https://www.tep.com/outage-center/"),
    ("IDAHO_POWER", "Idaho Power", "IDACORP", "ID,OR", 630, "arcgis",
     "https://www.idahopower.com/outages-safety/outages/outage-map/"),
    ("PORTLAND_GE", "Portland General Electric", "PGE", "OR", 950, "kubra",
     "https://portlandgeneral.com/outages/outage-map"),
    ("AVISTA", "Avista Utilities", "Avista Corp", "WA,ID", 410, "kubra",
     "https://www.myavista.com/outages/outage-map"),
    ("ALABAMA_POWER", "Alabama Power", "Southern Company", "AL", 1500, "kubra",
     "https://www.outagemap.alabamapower.com/"),
    ("MISSISSIPPI_POWER", "Mississippi Power", "Southern Company", "MS", 190, "kubra",
     "https://www.outagemap.mississippipower.com/"),
    ("GULF_POWER", "Florida Power & Light (Northwest FL)", "NextEra Energy", "FL", 470, "kubra",
     "https://www.fpl.com/outages/power-tracker.html"),
    ("TVA_MLGW", "Memphis Light Gas & Water", "Municipal (TVA)", "TN", 430, "arcgis",
     "https://www.mlgw.com/outages"),
    ("LADWP", "Los Angeles Dept of Water & Power", "Municipal", "CA", 1500, "arcgis",
     "https://www.ladwp.com/account/outages/power-outages"),
    ("SRP", "Salt River Project", "Public power", "AZ", 1100, "arcgis",
     "https://www.srpnet.com/outages/map"),
    ("CPS_ENERGY", "CPS Energy", "Municipal (San Antonio)", "TX", 920, "kubra",
     "https://outagemap.cpsenergy.com/"),
    ("AUSTIN_ENERGY", "Austin Energy", "Municipal", "TX", 560, "arcgis",
     "https://outagemap.austinenergy.com/"),
    ("SMUD", "Sacramento Municipal Utility District", "Public power", "CA", 660, "arcgis",
     "https://www.smud.org/Outages"),
    ("SEATTLE_CITY", "Seattle City Light", "Municipal", "WA", 480, "arcgis",
     "https://www.seattle.gov/city-light/outages"),
    ("JEA", "JEA", "Municipal (Jacksonville)", "FL", 500, "arcgis",
     "https://www.jea.com/outages/"),
    ("OUC", "Orlando Utilities Commission", "Municipal", "FL", 260, "kubra",
     "https://www.ouc.com/account-services/outages"),
    ("NPPD", "Nebraska Public Power District", "Public power", "NE", 600, "arcgis",
     "https://www.nppd.com/outages"),
    ("OPPD", "Omaha Public Power District", "Public power", "NE", 420, "arcgis",
     "https://www.oppd.com/outages-safety/view-outage-map/"),
    ("SANTEE_COOPER", "Santee Cooper", "Public power", "SC", 210, "kubra",
     "https://www.santeecooper.com/outages/"),
    ("CLECO", "Cleco Power", "Cleco", "LA", 290, "kubra",
     "https://www.cleco.com/outage-center"),
    ("PNM_TNMP", "Texas-New Mexico Power", "TXNM Energy", "TX", 270, "kubra",
     "https://www.tnmp.com/outages"),
    ("OG_E", "Oklahoma Gas & Electric (OG&E)", "OGE Energy", "OK,AR", 900, "kubra",
     "https://www.oge.com/wps/portal/ord/outages/outage-map"),
    ("WESTAR_EVERGY_KS", "Evergy (Kansas)", "Evergy", "KS", 750, "kubra",
     "https://www.evergy.com/outages/view-outages"),
    ("KCPL_EVERGY_MO", "Evergy (Missouri)", "Evergy", "MO", 850, "kubra",
     "https://www.evergy.com/outages/view-outages"),
    ("WPS", "Wisconsin Public Service", "WEC Energy Group", "WI", 460, "kubra",
     "https://www.wisconsinpublicservice.com/outages/outage-map"),
    ("AVANGRID_CMP", "Central Maine Power", "Avangrid", "ME", 650, "kubra",
     "https://www.cmpco.com/outages"),
    ("AVANGRID_NYSEG", "New York State Electric & Gas (NYSEG)", "Avangrid", "NY", 900, "kubra",
     "https://www.nyseg.com/outages"),
    ("AVANGRID_RGE", "Rochester Gas & Electric", "Avangrid", "NY", 380, "kubra",
     "https://www.rge.com/outages"),
    ("AVANGRID_UI", "United Illuminating", "Avangrid", "CT", 340, "kubra",
     "https://www.uinet.com/outages"),
    ("UNITIL", "Unitil", "Unitil Corp", "NH,MA,ME", 110, "kubra",
     "https://www.unitil.com/outages"),
    ("LIPA", "PSEG Long Island", "LIPA", "NY", 1100, "kubra",
     "https://www.psegliny.com/outages"),
    ("DOMINION_OH", "Duke Energy Ohio", "Duke Energy", "OH,KY", 870, "kubra",
     "https://www.duke-energy.com/outages/current-outages"),
    ("DUKE_INDIANA", "Duke Energy Indiana", "Duke Energy", "IN", 880, "kubra",
     "https://www.duke-energy.com/outages/current-outages"),
    ("EMERA_TAMPA", "Tampa Electric (TECO)", "Emera", "FL", 830, "kubra",
     "https://www.tampaelectric.com/outage/"),
    ("PEDERNALES", "Pedernales Electric Cooperative", "Cooperative", "TX", 360, "kubra",
     "https://www.pec.coop/outage-center/"),
    ("SOUTH_RIVER_EMC", "Sawnee EMC", "Cooperative", "GA", 190, "kubra",
     "https://www.sawnee.com/outages"),
    ("BLUE_RIDGE_EMC", "Blue Ridge Energy", "Cooperative", "NC", 80, "kubra",
     "https://www.blueridgeenergy.com/outages"),
]


def main() -> None:
    # Rank strictly by customer count so "work top-down by rank" means
    # "biggest coverage first". Ties broken by name for stable ordering.
    ordered = sorted(UTILITIES, key=lambda u: (-u[4], u[1]))
    rows = []
    for rank, (uid, name, parent, states, cust, plat, url) in enumerate(ordered, 1):
        rows.append({
            "rank": rank, "utility_id": uid, "utility_name": name,
            "parent": parent, "states": states, "customers_k": cust,
            "platform_guess": plat, "outage_map_url": url,
        })

    # CSV
    csv_path = OUT / "top_utilities.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # registry_starter.json - real registry shape, every entry disabled until verified.
    entries = []
    for r in rows:
        entry = {
            "utility_id": r["utility_id"],
            "utility_name": r["utility_name"],
            "platform": r["platform_guess"],
            "states": r["states"].split(","),
            "customers_served": r["customers_k"] * 1000,
            "enabled": False,
            "_priority_rank": r["rank"],
            "_outage_map_url": r["outage_map_url"],
            "_comment": "VERIFY in notebook 01: open _outage_map_url, DevTools "
                        "> Network, capture real endpoints, fill config, then "
                        "set enabled:true.",
            "config": {},
        }
        if r["platform_guess"] == "kubra":
            entry["config"] = {
                "metadata_url": "FILL-ME via DevTools",
                "tile_url_template": "FILL-ME via DevTools",
                "min_zoom": 1, "max_zoom": 14, "seed_quadkeys": [],
            }
        else:
            entry["config"] = {
                "service_url": "FILL-ME via DevTools",
                "customers_field": "CustomersAffected", "where": "1=1",
            }
        entries.append(entry)

    json_path = OUT / "registry_starter.json"
    json_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    n_kubra = sum(1 for r in rows if r["platform_guess"] == "kubra")
    print(f"{len(rows)} utilities -> {csv_path.name}, {json_path.name}")
    print(f"  platform guesses: {n_kubra} kubra, {len(rows) - n_kubra} arcgis")
    print(f"  total approx customers: {sum(r['customers_k'] for r in rows) / 1000:.1f} M")


if __name__ == "__main__":
    main()
