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

def main():
    pass


if __name__ == "__main__":
    main()
