import streamlit as st
import os
import datetime
from typing import Tuple, Optional, List
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from folium.plugins import MarkerCluster

# ==== Kakao API설치====
KAKAO_API_KEY = "72a8d42e1f121df307e0deb0f132ff66"

def get_address_from_coords(lat, lon):
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"x": lon, "y": lat}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        result = response.json()
        if result and isinstance(result, dict) and result.get("documents") and len(result["documents"]) > 0:
            address_info = result["documents"][0]
            road_address = address_info.get("road_address", {}).get("address_name")
            jibun_address = address_info.get("address", {}).get("address_name")
            return road_address if road_address else jibun_address
        else:
            st.warning("해당 위치에는 주소 정보가 없습니다. 다른 위치를 선택해 주세요.")
            return "주소 정보 없음"
    except requests.exceptions.RequestException as e:
        st.error(f"Kakao API 요청 실패: {e}")
        return "주소 변환 실패"
    except Exception as e:
        st.error(f"주소 변환 중 오류 발생: {e}")
        return "주소 변환 오류"

#====지도====
INITIAL_MAP_CENTER = [37.5665, 126.9780]
INITIAL_MAP_ZOOM = 12   
def display_interactive_map():
    st.subheader("1. 지도에서 민원 위치 선택")
    if "map_center" not in st.session_state:
        st.session_state.map_center = INITIAL_MAP_CENTER
    if "selected_map_coordinates" not in st.session_state:
        st.session_state.selected_map_coordinates = None
    if "selected_korean_address" not in st.session_state:
        st.session_state.selected_korean_address = ""

    m = folium.Map(location=st.session_state.map_center, zoom_start=INITIAL_MAP_ZOOM)
    if st.session_state.selected_map_coordinates:
        folium.Marker(
            location=st.session_state.selected_map_coordinates,
            popup=st.session_state.selected_korean_address or "선택된 위치",
            tooltip=st.session_state.selected_korean_address or "선택된 위치"
        ).add_to(m)

    map_data = st_folium(m, width=700, height=500, key="interactive_map")
    if map_data and map_data.get("last_clicked"):
        last_click = map_data["last_clicked"]
        clicked_coords_tuple = (last_click["lat"], last_click["lng"])
        if clicked_coords_tuple != st.session_state.selected_map_coordinates:
            st.session_state.selected_map_coordinates = clicked_coords_tuple
            st.session_state.map_center = [last_click["lat"], last_click["lng"]]
            address = get_address_from_coords(last_click["lat"], last_click["lng"])
            st.session_state.selected_korean_address = address if address else "주소를 찾을 수 없습니다."

    if st.session_state.selected_map_coordinates:
        lat, lon = st.session_state.selected_map_coordinates
        st.success(f"선택된 좌표: 위도 {lat:.5f}, 경도 {lon:.5f}")
        if st.session_state.selected_korean_address:
            st.info(f"자동 인식된 주소: {st.session_state.selected_korean_address}")
    else:
        st.info("지도에서 민원 발생 위치를 클릭해주세요.")

    return st.session_state.selected_map_coordinates, st.session_state.selected_korean_address

def display_overview_map(minwons: List[Minwon]):
    st.subheader("🗺️ 전체 민원 위치 보기 (유형별 그룹)")
    map_view = folium.Map(location=INITIAL_MAP_CENTER, zoom_start=INITIAL_MAP_ZOOM)
    marker_cluster = MarkerCluster().add_to(map_view)

    points_added = 0
    for mw in minwons:
        if mw.coordinates:
            popup_text = f"<b>{mw.title}</b><br>유형: {mw.category}<br>내용: {mw.content[:30]}..."
            folium.Marker(
                location=mw.coordinates,
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=mw.title,
                icon=folium.Icon(color=category_colors.get(mw.category, "lightgray"))
            ).add_to(marker_cluster)
            points_added +=1

    if points_added > 0:
        st_folium(map_view, width=700, height=500, key="overview_map")
    else:
        st.info("지도에 표시할 좌표가 있는 민원이 없습니다.")


#====유형/날짜별 시각화====
def show_category_statistics(minwons: List[Minwon]):
    st.subheader("📊 민원 유형별 통계")
    if minwons:
        df = pd.DataFrame([{"유형": mw.category} for mw in minwons])
        category_counts = df["유형"].value_counts()
        if not category_counts.empty:
            st.bar_chart(category_counts)
        else:
            st.info("통계에 사용할 민원 데이터가 없습니다.")
    else:
        st.info("민원 데이터가 없어 유형별 통계를 표시할 수 없습니다.")

def show_date_statistics(minwons: List[Minwon]):
    st.subheader("📅 날짜별 민원 제출 현황")
    if not minwons:
        st.info("민원 데이터가 없어 날짜별 통계를 표시할 수 없습니다.")
        return

    dates = [mw.date for mw in minwons if mw.date]
    if not dates:
        st.info("민원 데이터에 유효한 날짜 정보가 없어 통계를 표시할 수 없습니다.")
        return

    df = pd.DataFrame({"날짜": dates})
    df["날짜"] = pd.to_datetime(df["날짜"])
    date_counts = df["날짜"].dt.date.value_counts().sort_index()
    if date_counts.empty:
        st.info("날짜별 제출 현황을 집계할 수 없습니다.")
    else:
        st.bar_chart(date_counts)
def main():
    pass


if __name__ == "__main__":
    main()
