import streamlit as st
st.set_page_config(page_title="민원 접수 및 조회 시스템", layout="wide")
from minwon_core import Minwon, save_minwon_to_gsheet, load_minwons_from_gsheet, increment_like_count_in_gsheet, mark_minwon_as_solved_in_gsheet
import folium
from streamlit_folium import st_folium
import pandas as pd



def main():
    pass


if __name__ == "__main__":
    main()
