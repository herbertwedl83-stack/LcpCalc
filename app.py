"""
LCP CW 53 kW – Online Leistungs- und Wassermengen-Rechner
----------------------------------------------------------
Dieses Tool berechnet für verschiedene Leistungspunkte die benötigten
Kühlwassermengen, Ventilstellungen, Druckverluste, Lüftersteuerung
sowie Ablufttemperaturen eines Rittal LCP CW Systems.

Zusätzlich ermöglicht es einen ΔT-Sweep über einen frei wählbaren
Leistungswert, inklusive Diagramm und Exportfunktionen.

Technologien:
- Python
- Streamlit
- pandas
- matplotlib
"""

# ============================================================
# Imports
# ============================================================
import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt


# ============================================================
# Physikalische Konstanten
# ============================================================
CP_WATER = 4.186        # Spezifische Wärmekapazität von Wasser [kJ/kgK]
DENSITY_WATER = 0.998   # Dichte von Wasser [kg/l]


# ============================================================
# Hilfsfunktionen (Physikalische Modelle)
# ============================================================
def calc_flow(P_kW: float, deltaT: float) -> float:
    """
    Berechnet den benötigten Wasservolumenstrom in l/min.
    Formel:
        m_dot = P / (cp * DeltaT)
        Umrechnung: kg/s → l/min
    """
    m_dot_kg_s = (P_kW * 1000) / (CP_WATER * 1000 * deltaT)
    return m_dot_kg_s * 60 / DENSITY_WATER


def calc_abluft(Tin_server: float, P_kW: float, flow_l_min: float) -> float:
    """
    Berechnet die Ablufttemperatur hinter dem Server.
    Formel:
        ΔT = P / (m_dot * cp)
        T_out = T_in + ΔT
    """
    if flow_l_min == 0:
        return Tin_server

    m_dot_kg_s = flow_l_min / 60 * DENSITY_WATER
    deltaT = (P_kW * 1000) / (m_dot_kg_s * CP_WATER * 1000)
    return Tin_server + deltaT


def calc_pressure_loss(flow: float, maxflow: float) -> float:
    """
    Druckverlustmodell (quadratische Approximation)
    """
    if maxflow == 0:
        return 0
    return (flow / maxflow) ** 2 * 100


def calc_fan_speed(server_temp: float, water_in_temp: float) -> float:
    """
    Simple lineare Modellierung der Lüfterleistung.
    """
    delta = server_temp - water_in_temp
    return max(20, min(100, delta * 5))


# ============================================================
# Streamlit – Seiteneinstellungen
# ============================================================
st.set_page_config(page_title="LCP CW 53 kW Rechner", layout="wide")
st.title("🌐 LCP CW Leistungs- und Wassermengen-Rechner")


# ============================================================
# Eingabebereich
# ============================================================
col1, col2, col3 = st.columns(3)

water_in = col1.number_input("Wasser Eintrittstemperatur (°C)", 1.0, 40.0, 13.0)
deltaT = col1.number_input("ΔT Wasser maximal (°C)", 1.0, 30.0, 6.0)
server_in = col1.number_input("Server Luft Eintritt (°C)", 5.0, 45.0, 21.0)

maxflow = col2.number_input("Max Flow (l/min)", 10.0, 300.0, 140.0)
roomT = col2.number_input("Raumtemperatur (°C)", 1.0, 50.0, 23.0)
RH = col2.number_input("Luftfeuchte (%)", 1.0, 100.0, 30.0)

# Benutzer kann jetzt die Leistung für den ΔT‑Sweep frei wählen
sweep_power = col3.number_input("Leistung für ΔT Sweep (kW)", 5.0, 100.0, 30.0)

run = st.button("Berechnen")


# Leistungsstufen für Haupttabelle
powers = [10, 20, 30, 40, 50]


# ============================================================
# Hauptberechnung
# ============================================================
if run:

    # --------------------------------------------------------
    # Haupttabelle (10–50 kW)
    # --------------------------------------------------------
    rows = []

    for P in powers:

        flow = calc_flow(P, deltaT)
        valve = min(100, flow / maxflow * 100)
        loss = calc_pressure_loss(flow, maxflow)
        fan = calc_fan_speed(server_in, water_in)
        abluft = calc_abluft(server_in, P, flow)

        ruecklauf = water_in + deltaT  # feste Rücklauftemperatur

        rows.append([
            f"{P} kW",
            round(flow, 2),
            round(valve, 1),
            round(loss, 1),
            round(fan, 1),
            round(abluft, 2),
            round(ruecklauf, 2)
        ])

    df_main = pd.DataFrame(rows, columns=[
        "Leistung", "Flow (l/min)", "Ventil (%)",
        "Druckverlust (%)", "Lüfter (%)",
        "Abluft (°C)", "Rücklauf (°C)"
    ])

    st.subheader("📋 Leistungsstufen-Tabelle")
    st.dataframe(df_main, use_container_width=True)


    # --------------------------------------------------------
    # Diagramm 1 – Flow vs Leistung
    # --------------------------------------------------------
    st.subheader("📉 Flow vs Leistung")

    fig1, ax1 = plt.subplots()
    ax1.plot(df_main["Leistung"], df_main["Flow (l/min)"], marker="o")
    ax1.set_xlabel("Leistung (kW)")
    ax1.set_ylabel("Flow (l/min)")
    ax1.grid(True)
    st.pyplot(fig1)


    # --------------------------------------------------------
    # ΔT Sweep (frei wählbare Leistung)
    # --------------------------------------------------------
    st.subheader(f"📈 ΔT Sweep – Flow & Abluft bei {sweep_power:.0f} kW")

    sweep_dTs = list(range(1, int(deltaT)+1, 2))

    sweep_flows = [calc_flow(sweep_power, dt) for dt in sweep_dTs]
    sweep_abluft = [calc_abluft(server_in, sweep_power, f) for f in sweep_flows]

    df_sweep = pd.DataFrame({
        "DeltaT (°C)": sweep_dTs,
        "Flow (l/min)": sweep_flows,
        "Abluft (°C)": sweep_abluft
    })

    st.dataframe(df_sweep, use_container_width=True)


    # --------------------------------------------------------
    # Diagramm 2 – Flow vs ΔT
    # --------------------------------------------------------
    fig2, ax2 = plt.subplots()
    ax2.plot(df_sweep["DeltaT (°C)"], df_sweep["Flow (l/min)"],
             marker="o", color="orange")
    ax2.set_xlabel("ΔT (°C)")
    ax2.set_ylabel("Flow (l/min)")
    ax2.set_title(f"Benötigte Wassermenge vs ΔT für {sweep_power:.0f} kW")
    ax2.grid(True)
    st.pyplot(fig2)


    # --------------------------------------------------------
    # Excel Export (Haupttabelle + Sweep)
    # --------------------------------------------------------
    st.subheader("📥 Excel Export")

    df_main.to_excel("leistungsdaten.xlsx", index=False)
    df_sweep.to_excel("deltat_sweep.xlsx", index=False)

    st.download_button(
        "📥 Leistungs-Tabelle herunterladen",
        data=open("leistungsdaten.xlsx", "rb").read(),
        file_name="LCP_Leistungsdaten.xlsx"
    )

    st.download_button(
        "📥 ΔT Sweep herunterladen",
        data=open("deltat_sweep.xlsx", "rb").read(),
        file_name="LCP_DeltaT_Sweep.xlsx"
    )
