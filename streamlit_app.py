import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Lomakiinteistöjen Data",
    page_icon="📊",
    layout="wide"
)

# --- Constants ---
DATA_FILE = os.path.join("datasets", "combined_holiday_properties.csv")
MAPPING_FILE = os.path.join("datasets", "kunta_maakunta_mapping.csv")
YEAR_COL = 'vuosi'
MUNICIPALITY_COL = 'aluejakoselite'
REGION_COL = 'maakunta'
SHORELINE_COL = 'rantatyyppi'
METRIC_COLS = {
    'lukumäärä': 'Lukumäärä (kpl)',
    'ka_pinta_ala_m2': 'Keskim. Pinta-ala (m²)',
    'mediaanihinta_eur': 'Mediaanihinta (€)',
    'keskihinta_eur': 'Keskihinta (€)'
}
SHORELINE_OPTIONS = {'Kaikki': None, 'Ranta': 'ranta', 'Ei rantaa': 'ei_rantaa'}
UNKNOWN_REGION = "Tuntematon"
AGGREGATION_LEVELS = ["Maakunta", "Kunta"]

# --- Data Loading ---
@st.cache_data
def load_mapping(file_path):
    """Loads kunta-maakunta mapping from CSV."""
    try:
        map_df = pd.read_csv(file_path, sep=';', encoding='utf-8')
        if 'kunta' in map_df.columns and 'maakunta' in map_df.columns:
            return map_df.set_index('kunta')['maakunta'].to_dict()
        else:
            st.warning(f"Mapping file {file_path} must contain 'kunta' and 'maakunta' columns.")
            return {}
    except FileNotFoundError:
        st.warning(f"Mapping file not found at: {file_path}. Regions cannot be determined.")
        return {}
    except Exception as e:
        st.error(f"Error loading mapping file: {e}")
        return {}

@st.cache_data
def load_data(data_file_path, mapping_dict):
    """Loads data from the CSV file and adds region column."""
    try:
        df = pd.read_csv(data_file_path, sep=';', encoding='utf-8')
        df[YEAR_COL] = pd.to_numeric(df[YEAR_COL], errors='coerce')
        for col in METRIC_COLS.keys():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce')
        df = df.dropna(subset=[YEAR_COL])
        df[YEAR_COL] = df[YEAR_COL].astype(int)
        df[MUNICIPALITY_COL] = df[MUNICIPALITY_COL].astype(str)
        df[SHORELINE_COL] = df[SHORELINE_COL].astype(str)

        if mapping_dict:
            df[REGION_COL] = df[MUNICIPALITY_COL].map(mapping_dict).fillna(UNKNOWN_REGION)
        else:
            df[REGION_COL] = UNKNOWN_REGION
        df[REGION_COL] = df[REGION_COL].astype(str)

        return df
    except FileNotFoundError:
        st.error(f"Data file not found at: {data_file_path}")
        return None
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

kunta_maakunta_map = load_mapping(MAPPING_FILE)
data = load_data(DATA_FILE, kunta_maakunta_map)

# --- Main App Logic ---
if data is not None:
    st.title("📊 Lomakiinteistöjen Hintakehitys ja Määrät")
    st.markdown("Analysoi lomakiinteistöjen kauppahintoja ja määriä Suomessa vuosien varrella.")

    st.sidebar.header("Suodattimet")

    # --- Aggregation Level Selection (New) ---
    selected_agg_level = st.sidebar.radio(
        "Valitse Aluetaso",
        options=AGGREGATION_LEVELS,
        index=0 # Default to Maakunta
    )

    # --- Conditional Area Selection ---
    selected_areas = []
    if selected_agg_level == "Maakunta":
        all_regions = sorted([r for r in data[REGION_COL].unique() if r != UNKNOWN_REGION])
        selected_areas = st.sidebar.multiselect(
            "Valitse Maakunta/Maakunnat",
            options=all_regions,
            default=all_regions[0] if all_regions else [] # Default to first region if available
        )
    elif selected_agg_level == "Kunta":
        all_municipalities = sorted(data[MUNICIPALITY_COL].unique())
        selected_areas = st.sidebar.multiselect(
            "Valitse Kunta/Kunnat",
            options=all_municipalities,
            default=all_municipalities[0] if all_municipalities else [] # Default to first municipality if available
        )

    # Year Range Slider
    min_year, max_year = int(data[YEAR_COL].min()), int(data[YEAR_COL].max())
    selected_years = st.sidebar.slider(
        "Valitse Vuosiväli",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )

    # Shoreline Type Radio Buttons
    selected_shoreline_label = st.sidebar.radio(
        "Rantatyyppi",
        options=list(SHORELINE_OPTIONS.keys()),
        index=0
    )
    selected_shoreline_value = SHORELINE_OPTIONS[selected_shoreline_label]

    # Metric Selection
    selected_metric_key = st.sidebar.selectbox(
        "Valitse Mittari",
        options=list(METRIC_COLS.keys()),
        format_func=lambda x: METRIC_COLS[x]
    )
    selected_metric_label = METRIC_COLS[selected_metric_key]

    # --- Filtering Data --- 
    if not selected_areas:
        st.sidebar.warning(f"Valitse vähintään yksi {selected_agg_level.lower()}.")
        st.stop()

    # Filter by selected aggregation level and areas
    filter_col = REGION_COL if selected_agg_level == "Maakunta" else MUNICIPALITY_COL
    filtered_data = data[data[filter_col].isin(selected_areas)]

    # Apply year filter
    filtered_data = filtered_data[
        (filtered_data[YEAR_COL] >= selected_years[0]) &
        (filtered_data[YEAR_COL] <= selected_years[1])
    ]

    # Apply shoreline filter
    if selected_shoreline_value is not None:
        filtered_data = filtered_data[filtered_data[SHORELINE_COL] == selected_shoreline_value]

    # If aggregating by Maakunta, group the data for charting
    if selected_agg_level == "Maakunta":
        group_cols = [REGION_COL, YEAR_COL]
        if selected_shoreline_label == 'Kaikki':
             group_cols.append(SHORELINE_COL)

        # Calculate weighted average for prices/area, sum for count
        agg_funcs = {}
        if 'lukumäärä' in filtered_data.columns:
            agg_funcs['lukumäärä'] = 'sum'
        if 'ka_pinta_ala_m2' in filtered_data.columns and 'lukumäärä' in filtered_data.columns:
             # Weighted average: sum(area * count) / sum(count)
             filtered_data['weighted_area'] = filtered_data['ka_pinta_ala_m2'] * filtered_data['lukumäärä']
             agg_funcs['weighted_area'] = 'sum'
        if 'keskihinta_eur' in filtered_data.columns and 'lukumäärä' in filtered_data.columns:
             filtered_data['weighted_avg_price'] = filtered_data['keskihinta_eur'] * filtered_data['lukumäärä']
             agg_funcs['weighted_avg_price'] = 'sum'
        # Note: Median price aggregation is tricky. Simply taking the median of medians is often misleading.
        # We will display the median price only when Kunta level is selected or for a single Maakunta.
        if 'mediaanihinta_eur' in filtered_data.columns and len(selected_areas) == 1:
             agg_funcs['mediaanihinta_eur'] = 'median' # Approximate median for a single region

        if agg_funcs:
             chart_data = filtered_data.groupby(group_cols, as_index=False).agg(agg_funcs)
             # Calculate final weighted averages
             if 'weighted_area' in chart_data.columns and 'lukumäärä' in chart_data.columns:
                  chart_data['ka_pinta_ala_m2'] = chart_data['weighted_area'] / chart_data['lukumäärä']
                  chart_data.drop(columns=['weighted_area'], inplace=True)
             if 'weighted_avg_price' in chart_data.columns and 'lukumäärä' in chart_data.columns:
                  chart_data['keskihinta_eur'] = chart_data['weighted_avg_price'] / chart_data['lukumäärä']
                  chart_data.drop(columns=['weighted_avg_price'], inplace=True)
        else:
             chart_data = pd.DataFrame() # Empty df if no metrics could be aggregated

        # Handle case where median price couldn't be aggregated for multiple regions
        if selected_metric_key == 'mediaanihinta_eur' and len(selected_areas) > 1:
             st.warning("Mediaanihintaa ei voida luotettavasti aggregoida usealle maakunnalle. Valitse 'Keskihinta' tai tarkastele maakuntia yksitellen.")
             chart_data = pd.DataFrame() # Don't show misleading median chart

    else: # Kunta level selected
        chart_data = filtered_data

    # --- Charting ---
    st.header(f"{selected_metric_label} Kehitys")

    line_chart_displayed = False # Flag to track if line chart was shown
    if not chart_data.empty and selected_metric_key in chart_data.columns:
        color_col = None
        if len(selected_areas) > 1:
            color_col = filter_col # Color by the selected aggregation level column
        elif len(selected_areas) == 1 and selected_shoreline_label == 'Kaikki':
             color_col = SHORELINE_COL

        title_parts = [selected_metric_label, "/ Vuosi", f"({selected_agg_level}: {', '.join(selected_areas)})" ]
        chart_title = " ".join(title_parts)

        fig = px.line(
            chart_data.sort_values(by=[filter_col, YEAR_COL]),
            x=YEAR_COL,
            y=selected_metric_key,
            color=color_col,
            title=chart_title,
            labels={
                YEAR_COL: "Vuosi",
                selected_metric_key: selected_metric_label,
                MUNICIPALITY_COL: "Kunta",
                REGION_COL: "Maakunta",
                SHORELINE_COL: "Rantatyyppi"
            },
            markers=True
        )
        fig.update_layout(xaxis_title="Vuosi", yaxis_title=selected_metric_label)
        st.plotly_chart(fig, use_container_width=True)
        line_chart_displayed = True # Set flag

    elif selected_metric_key != 'mediaanihinta_eur' or len(selected_areas) == 1 or selected_agg_level != "Maakunta":
         # Only show 'No data' if it wasn't the intentional warning about median aggregation
        st.warning("Ei dataa aikasarjakuvaajaan valituilla suodattimilla tai valittua mittaria ei voitu laskea.")

    # --- Bar Chart Comparison (New Section) ---
    st.header(f"{selected_metric_label} Vertailu Rantatyypeittäin")

    if selected_metric_key == 'mediaanihinta_eur':
        st.info("Mediaanihintaa ei voida mielekkäästi verrata tässä kuvaajassa keskiarvoistamalla.")
    elif not filtered_data.empty:
        # Prepare data for bar chart: Average metric over the period, grouped by area and shoreline type
        group_cols_bar = [filter_col, SHORELINE_COL]

        # Use weighted averages if Maakunta level for area/price, simple average for count
        agg_funcs_bar = {}
        if selected_metric_key == 'lukumäärä':
             # Average the yearly count over the period
             agg_funcs_bar[selected_metric_key] = 'mean'
        elif selected_metric_key == 'ka_pinta_ala_m2' and 'lukumäärä' in filtered_data.columns:
             # Overall weighted average for the period
             temp_df_bar = filtered_data.copy()
             temp_df_bar['total_area'] = temp_df_bar['ka_pinta_ala_m2'] * temp_df_bar['lukumäärä']
             summary_bar = temp_df_bar.groupby(group_cols_bar).agg(total_area=('total_area', 'sum'), total_count=('lukumäärä', 'sum')).reset_index()
             summary_bar[selected_metric_key] = summary_bar['total_area'] / summary_bar['total_count']
             bar_chart_data = summary_bar
        elif selected_metric_key == 'keskihinta_eur' and 'lukumäärä' in filtered_data.columns:
             # Overall weighted average for the period
             temp_df_bar = filtered_data.copy()
             temp_df_bar['total_price'] = temp_df_bar['keskihinta_eur'] * temp_df_bar['lukumäärä']
             summary_bar = temp_df_bar.groupby(group_cols_bar).agg(total_price=('total_price', 'sum'), total_count=('lukumäärä', 'sum')).reset_index()
             summary_bar[selected_metric_key] = summary_bar['total_price'] / summary_bar['total_count']
             bar_chart_data = summary_bar
        else:
             # Fallback for other metrics or if count isn't available - simple average
             try:
                bar_chart_data = filtered_data.groupby(group_cols_bar, as_index=False)[selected_metric_key].mean()
             except Exception:
                 bar_chart_data = pd.DataFrame() # Handle potential errors during mean calculation

        if not bar_chart_data.empty and selected_metric_key in bar_chart_data.columns:
            fig_bar = px.bar(
                bar_chart_data.sort_values(by=[filter_col, SHORELINE_COL]),
                x=filter_col,
                y=selected_metric_key,
                color=SHORELINE_COL,
                barmode='group', # Group bars side-by-side
                title=f"Keskimääräinen {selected_metric_label} / Rantatyyppi ({selected_years[0]}-{selected_years[1]})",
                labels={
                    filter_col: selected_agg_level,
                    selected_metric_key: f"Keskim. {selected_metric_label} ({selected_years[0]}-{selected_years[1]})",
                    SHORELINE_COL: "Rantatyyppi"
                }
            )
            fig_bar.update_layout(xaxis_title=selected_agg_level, yaxis_title=f"Keskim. {selected_metric_label}")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
             st.warning("Ei dataa pylväskuvaajaan valituilla suodattimilla.")
    else:
         # This condition might be redundant if the main filtered_data check handles it
         st.warning("Ei dataa pylväskuvaajaan valituilla suodattimilla.")

    # --- Data Table ---
    st.header("Suodatettu Data")
    # Always show the raw filtered data before aggregation
    display_cols = [YEAR_COL, REGION_COL, MUNICIPALITY_COL, SHORELINE_COL] + list(METRIC_COLS.keys())
    display_cols = [col for col in display_cols if col in filtered_data.columns]
    st.dataframe(filtered_data[display_cols].sort_values(by=[YEAR_COL, REGION_COL, MUNICIPALITY_COL]), use_container_width=True)

else:
    st.error("Failed to load data. Cannot display the application.")

st.sidebar.markdown("---")
st.sidebar.info("Aja komennolla: `streamlit run streamlit_app.py`") 