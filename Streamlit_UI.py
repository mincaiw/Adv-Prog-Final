import streamlit as st
import os
import datetime
from typing import Tuple, Optional, List
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from folium.plugins import MarkerCluster
from minwon_core import Minwon, save_minwon_to_gsheet, load_minwons_from_gsheet, increment_like_count_in_gsheet, mark_minwon_as_solved_in_gsheet


# ==== Kakao API설치====
KAKAO_API_KEY = "a34b932ea6ee81a3d6634de738ef60f3"

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

# ====입력 필드====
def get_minwon_title_input() -> str:
    return st.text_input("민원 제목:", key="minwon_title_input", placeholder="민원의 주요 내용을 간략하게 입력해주세요.")

def get_minwon_content_input() -> str:
    return st.text_area("민원 내용:", height=150, key="minwon_content_input", placeholder="상세한 민원 내용을 작성해주세요.")

def get_minwon_category_input() -> str:
    categories = ["교통 불편", "환경 문제", "시설 개선", "안전 문제", "기타 건의"]
    return st.selectbox("민원 유형:", categories, key="minwon_category_input")

def get_minwon_date_input() -> datetime.date:
    return st.date_input("날짜 선택:", value=datetime.date.today(), key="minwon_date_input")

def get_minwon_author_input() -> str:
    return st.text_input("제출자 이름 (선택 사항):", key="minwon_author_input", placeholder="이름을 남겨주세요.")

#====지도====
INITIAL_MAP_CENTER = [37.5665, 126.9780]
INITIAL_MAP_ZOOM = 12

category_colors = {
    "교통 불편": "red",
    "환경 문제": "green",
    "시설 개선": "blue",
    "안전 문제": "orange",
    "기타 건의": "gray"
}

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

# ==== 좋아요/상태변경 ====
def display_minwon_instance(minwon_item: Minwon):
    st.markdown(minwon_item.to_display_string())

    like_count = minwon_item.like_count
    button_label = f"👍 추천 ({like_count})"
    if st.button(button_label, key=f"like_button_{minwon_item.id}"):
        if GOOGLE_SHEETS_ENABLED:
            success = increment_like_count_in_gsheet(minwon_item.id)
            if success:
                st.session_state.minwons_list = load_minwons_from_gsheet()
                st.rerun()
            else:
                st.error("추천 수를 업데이트하는 데 실패했습니다.")
        else:
            st.warning("Google Sheets에 연결되지 않아 추천 수를 기록할 수 없습니다.")

    if minwon_item.status != "처리완료":
        if st.button("이 민원을 처리완료로 변경", key=f"solve_btn_{minwon_item.id}"):
            if mark_minwon_as_solved_in_gsheet(minwon_item.id):
                st.success("상태가 '처리완료'로 변경되었습니다!")
                st.session_state.minwons_list = load_minwons_from_gsheet()
                st.rerun()
    st.markdown("---")

def main():
    if 'minwons_list' not in st.session_state: # 세션 상태 변수명 변경
        if GOOGLE_SHEETS_ENABLED:
            with st.spinner("Google Sheets에서 데이터를 불러오는 중..."): # 로딩 스피너 추가
                st.session_state.minwons_list = load_minwons_from_gsheet()
        else:
            st.session_state.minwons_list = []
    
    # 지도 관련 세션 상태 초기화는 display_interactive_map 함수 내부에서 처리
    if "map_center" not in st.session_state: st.session_state.map_center = INITIAL_MAP_CENTER
    if "selected_map_coordinates" not in st.session_state: st.session_state.selected_map_coordinates = None
    if "selected_korean_address" not in st.session_state: st.session_state.selected_korean_address = ""


    st.sidebar.header("⚙️ 작업 메뉴") # 사이드바 헤더 변경
    app_mode_options = {
        "새 민원 제출": "submit_new",
        "전체 민원 보기": "view_all",   
        "추천 순위 보기": "view_ranking", 
        "새로고침 (Google Sheets)": "refresh_gsheet" 
    }
    selected_mode_korean = st.sidebar.selectbox(
        "모드 선택:",
        list(app_mode_options.keys()),
        key="app_mode_selectbox"
    )
    app_mode = app_mode_options[selected_mode_korean]


    if app_mode == "submit_new":
        st.header("➕ 새 민원 제출")
        
        # 지도에서 위치 선택 및 주소 자동 변환
        coords, auto_korean_address = display_interactive_map()
        
        st.subheader("2. 민원 상세 정보 입력")
        title = get_minwon_title_input()
        content = get_minwon_content_input()
        category = get_minwon_category_input()
        date = get_minwon_date_input()
        author = get_minwon_author_input()
        
        # 주소 입력 필드: 자동 변환된 주소를 기본값으로 사용하고 수정 가능하도록 함
        current_korean_address = st.text_input(
            "주소 (지도에서 자동 인식 / 직접 수정 가능):", 
            value=st.session_state.selected_korean_address,
            key="korean_address_manual_input"
        )

        if st.button("민원 제출", key="submit_minwon_button", type="primary"):
            final_selected_coords = st.session_state.selected_map_coordinates
            
            if not title: st.error("민원 제목을 입력해주세요!")
            elif not content: st.error("민원 내용을 입력해주세요!")
            elif not final_selected_coords: st.error("지도에서 민원 위치를 선택해주세요!")
            else:
                new_minwon = Minwon(
                    title=title, content=content, date=date,
                    korean_address=current_korean_address, # 사용자가 수정한 주소 사용
                    coordinates=final_selected_coords, 
                    author=author or "익명", 
                    category=category,
                    like_count=0 
                )
                st.session_state.minwons_list.append(new_minwon)
                if GOOGLE_SHEETS_ENABLED: save_minwon_to_gsheet(new_minwon)
                else: st.info("Google Sheets에 연결되지 않아, 현재 세션에만 민원이 저장됩니다.")
                
                st.success("민원이 성공적으로 제출되었습니다!")
                with st.expander("제출된 민원 정보 보기", expanded=True): # 제출 후 바로 보이도록
                    display_minwon_instance(new_minwon)
                
                # 다음 제출을 위해 선택 사항 초기화
                st.session_state.selected_map_coordinates = None
                st.session_state.selected_korean_address = ""
                st.session_state.map_center = INITIAL_MAP_CENTER
                

    elif app_mode == "view_all":
        st.header("📜 전체 민원 목록")

        filter_status = st.radio(
        "상태별 보기", 
        options=["전체", "미해결", "처리완료"],
        horizontal=True
        )
        minwons_to_display = st.session_state.minwons_list

        if filter_status != "전체":
            minwons_to_display = [mw for mw in minwons_to_display if mw.status == filter_status]
        
        if not GOOGLE_SHEETS_ENABLED and not st.session_state.minwons_list:
             st.warning("Google Sheets에 연결되지 않았고, 현재 세션에 민원 데이터가 없습니다. 민원을 먼저 제출하거나 Google Sheets 연결을 확인해주세요.")
        
        search_author_query = st.text_input("제출자 이름으로 검색 (일부 입력 가능):", key="author_search_input")
        
        filtered_minwons = minwons_to_display
        if search_author_query.strip():
            filtered_minwons = [
                mw for mw in minwons_to_display 
                if mw.author and search_author_query.strip().lower() in mw.author.lower()
            ]
            st.info(f"'{search_author_query}'을(를) 포함하는 제출자의 민원 {len(filtered_minwons)}건이 검색되었습니다.")
        
        if not filtered_minwons:
            if search_author_query.strip():
                 st.info(f"'{search_author_query}'을(를) 포함하는 제출자의 민원 데이터가 없습니다.")
            else:
                 st.info("현재 등록된 민원 데이터가 없습니다.")
        else:
            sort_key_options = {"최신순": "date", "추천순": "like_count"}
            selected_sort_key_korean = st.selectbox("정렬 기준:", list(sort_key_options.keys()))
            sort_by = sort_key_options[selected_sort_key_korean]

            reverse_sort = True 
            
            sorted_minwons = sorted(
                filtered_minwons, 
                key=lambda mw: getattr(mw, sort_by, 0 if sort_by == "like_count" else datetime.date.min), 
                reverse=reverse_sort
            )

            for mw_item in sorted_minwons:
                display_minwon_instance(mw_item)
            
            with st.expander("지도에서 전체 민원 보기", expanded=False):
                display_overview_map(filtered_minwons)
            with st.expander("유형별 통계 보기", expanded=False):
                show_category_statistics(filtered_minwons)
            with st.expander("날짜별 통계 보기", expanded=False):
                show_date_statistics(filtered_minwons)
    
    elif app_mode == "view_ranking": # 점수 순위 보기
        st.header("👍 추천 순위 보기")
        if not st.session_state.minwons_list:
            st.info("표시할 민원 데이터가 없습니다.")
        else:
            # like_count 기준으로 내림차순 정렬
            minwons_sorted_by_likes = sorted(
                st.session_state.minwons_list, 
                key=lambda mw: mw.like_count, 
                reverse=True
            )
            
            for rank, mw in enumerate(minwons_sorted_by_likes):
                col1, col2 = st.columns([4,1])
                with col1:
                    st.markdown(f"**{rank+1}위. {mw.title}** (추천: {mw.like_count})")
                    st.caption(f"카테고리: {mw.category} | 작성자: {mw.author or '익명'} | 날짜: {mw.date}")
                with col2:
                    if st.button("상세보기", key=f"rank_detail_btn_{mw.id}"):
                        with st.expander(f"{mw.title} - 상세 정보", expanded=True):
                            display_minwon_instance(mw) 
                st.markdown("---")


    elif app_mode == "refresh_gsheet":
        st.header("📥 Google Sheets에서 데이터 새로고침")
        if not GOOGLE_SHEETS_ENABLED:
            st.error("Google Sheets에 연결되지 않아 데이터를 불러올 수 없습니다. token.json 파일과 인터넷 연결을 확인해주세요.")
        elif st.button("새로고침 시작", key="force_reload_gsheet_button"):
            with st.spinner("Google Sheets에서 최신 데이터를 불러오는 중..."):
                st.session_state.minwons_list = load_minwons_from_gsheet()
            st.success(f"Google Sheets에서 데이터를 성공적으로 새로고침했습니다. 현재 총 {len(st.session_state.minwons_list)}건의 민원이 있습니다.")
            # 데이터를 표시할 필요는 없으므로 rerun 하지 않거나, 사용자가 다른 뷰로 이동하도록 유도
            
    st.sidebar.markdown("---")
    st.sidebar.info(f"현재 세션에 {len(st.session_state.minwons_list)}건의 민원이 있습니다.")



if __name__ == "__main__":
    main()
