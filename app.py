import pandas as pd
import streamlit as st
import plotly.express as px

# ★ 추가: 본문을 넓게 사용
st.set_page_config(page_title="철도 데이터 분석 대시보드", layout="wide")

# 데이터 읽기
df = pd.read_csv("analysis_result.csv")
df["측정시각"] = pd.to_datetime(df["측정시각"], errors="coerce")

# ★ 추가: 날짜가 없는 자료 안내와 시간순 정렬
if df["측정시각"].isna().any():
    st.warning("측정시각을 확인할 수 없는 기록은 조회에서 제외합니다.")
df = df.dropna(subset=["설비ID", "측정시각"]).sort_values("측정시각")
if df.empty:
    st.warning("조회할 수 있는 설비와 측정시각이 없습니다.")
    st.stop()

# 제목과 설명
st.title("철도 데이터 분석 대시보드")
st.write("교육용 가상 자료입니다. AI 확인후보는 고장 확정이 아닙니다.")

# ★ 수정: 스크롤 바로가기 대신 화면 선택 메뉴
with st.sidebar:
    st.title("대시보드 메뉴")
    menu = st.radio("화면 선택", [
        "요약 지표", "조회 결과", "AI 점검 후보", "센서별 추이",
        "다음 1시간 온도 예측", "단순 예측과 성능 비교",
        "예측 오차가 큰 기록", "업무 검토 및 저장", "파일 내려받기",
    ])
    st.divider()
    st.subheader("설비 및 기간 선택")
    equipment = st.selectbox("설비 선택", df["설비ID"].unique())
    view = df[df["설비ID"] == equipment]
    start = st.date_input("시작일", view["측정시각"].min().date(), key=f"start_{equipment}")
    end = st.date_input("종료일", view["측정시각"].max().date(), key=f"end_{equipment}")
    st.caption("선택한 설비와 기간을 모든 화면에 적용합니다.")

# ★ 추가: 시작일과 종료일 검증
if start > end:
    st.warning("시작일은 종료일보다 늦을 수 없습니다. 날짜를 다시 선택하세요.")
    st.stop()

# ★ 시작일과 종료일을 모두 포함해 조회
view = view[(view["측정시각"].dt.date >= start) & (view["측정시각"].dt.date <= end)]

# ★ 추가: 조회 결과가 없으면 이후 계산 중단
if view.empty:
    st.warning("조회 결과가 없습니다. 날짜를 다시 선택하세요.")
    st.stop()

# ★ 추가: 상단 요약 지표
candidates = view[view["AI결과"] == "확인후보"]
pred = view.dropna(subset=["다음온도_C", "AI예측온도_C"]).copy()
mae = (pred["다음온도_C"] - pred["AI예측온도_C"]).abs().mean()
mae_text = f"{mae:.2f} ℃" if len(pred) > 0 else "평가 자료 없음"
# 판정이 있는 기록만 분모에 포함합니다.
ai_valid_count = view["AI결과"].isin(["확인후보", "모델미탐지"]).sum()
candidate_rate = len(candidates) / ai_valid_count * 100 if ai_valid_count else None
rate_text = f"{candidate_rate:.2f}%" if candidate_rate is not None else "판정 자료 없음"

st.caption(f"설비: {equipment} | 조회 기간: {start} ~ {end} (측정시각 기준)")

# ★ 수정: 비교 계산은 메뉴와 관계없이 실행
comparison = view.dropna(subset=["온도_C", "다음온도_C", "AI예측온도_C"]).copy()
comparison_report = "단순 예측과 AI 비교: 비교 자료 없음"
if not comparison.empty:
    baseline_mae = (comparison["다음온도_C"] - comparison["온도_C"]).abs().mean()
    comparison_ai_mae = (comparison["다음온도_C"] - comparison["AI예측온도_C"]).abs().mean()
    compare_table = pd.DataFrame({
        "예측 방법": ["단순 예측 현재 온도 유지", "AI 예측"],
        "MAE (℃)": [baseline_mae, comparison_ai_mae],
        "비교 건수": [len(comparison), len(comparison)],
    })
    difference = baseline_mae - comparison_ai_mae
    if abs(difference) < 0.000001:
        comparison_message = "선택한 기간의 동일 기록에서 두 방법의 MAE가 같습니다."
    elif difference > 0:
        comparison_message = f"선택한 기간의 동일 기록에서 AI의 MAE가 단순 예측보다 {difference:.3f} ℃ 작습니다."
    else:
        comparison_message = f"선택한 기간의 동일 기록에서 단순 예측의 MAE가 AI보다 {-difference:.3f} ℃ 작습니다."
    comparison_report = (
        f"단순 예측 MAE: {baseline_mae:.3f} ℃ / 동일 기록 AI MAE: {comparison_ai_mae:.3f} ℃ "
        f"({len(comparison)}건 비교)\n{comparison_message}"
    )


# ★ 수정: 선택한 메뉴의 화면만 표시
if menu == "요약 지표":
    st.subheader("요약 지표")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("조회 건수", len(view))
    col2.metric("AI 확인후보", len(candidates))
    col3.metric("AI 후보 비율", rate_text)
    col4.metric("온도 예측 MAE", mae_text)
    st.caption(f"AI 후보 비율은 판정이 있는 {ai_valid_count}건 기준이며, MAE는 실제·예측이 모두 있는 {len(pred)}건 기준입니다.")

# ★ 수정: 선택한 메뉴의 화면만 표시
if menu == "조회 결과":
    st.subheader("조회 결과")

    st.write("조회 행 수:", len(view))
    if len(view) == 0:
        st.warning("조회 결과가 없습니다. 날짜를 다시 선택하세요.")
    st.dataframe(view)

# ★ 수정: 선택한 메뉴의 화면만 표시
if menu == "AI 점검 후보":
    st.subheader("AI 점검 후보")
    candidates = view[view["AI결과"] == "확인후보"]
    st.metric("AI 확인후보 건수", len(candidates))
    st.dataframe(view["AI결과"].value_counts())

    fig = px.line(view, x="측정시각", y="온도_C", title="온도 추이와 AI 확인후보")
    fig.add_scatter(x=candidates["측정시각"], y=candidates["온도_C"],
                    mode="markers", name="확인후보", marker=dict(color="red", size=10))
    st.plotly_chart(fig)
    st.dataframe(candidates)

# ★ 수정: 선택한 메뉴의 화면만 표시
if menu == "센서별 추이":
    st.subheader("센서별 추이")

    available_sensors = [c for c in ["진동_mm_s", "전류_A", "부하율_pct"] if c in view.columns]
    if not available_sensors:
        st.info("진동·전류·부하율 열이 없어 그래프를 표시할 수 없습니다.")
    else:
        sensor_column = st.selectbox("확인할 센서", available_sensors)
        sensor_fig = px.line(view, x="측정시각", y=sensor_column, title=f"{sensor_column} 추이와 AI 확인후보")
        sensor_fig.add_scatter(
            x=candidates["측정시각"], y=candidates[sensor_column],
            mode="markers", name="확인후보", marker=dict(color="red", size=10),
        )
        st.plotly_chart(sensor_fig)

# ★ 수정: 선택한 메뉴의 화면만 표시
if menu == "다음 1시간 온도 예측":
    st.subheader("다음 1시간 온도 예측")
    pred = view.dropna(subset=["다음온도_C", "AI예측온도_C"])   # 실제·예측이 모두 있는 행
    mae = (pred["다음온도_C"] - pred["AI예측온도_C"]).abs().mean()
    st.metric("평균 절대 오차(MAE)", mae_text)
    st.write("비교한 자료:", len(pred), "건")

    # ★ 추가: 평가 자료가 없는 경우 안내
    st.caption("조회 기간은 측정시각 기준이며, 예측 대상인 목표시각은 종료일 이후일 수 있습니다.")
    if pred.empty:
        st.info("이 기간에는 실제 다음 온도와 AI 예측 온도가 모두 있는 자료가 없습니다.")
    else:
        plot_pred = pred.copy()
        plot_pred["목표시각"] = pd.to_datetime(plot_pred["목표시각"], errors="coerce")
        plot_pred = plot_pred.dropna(subset=["목표시각"]).sort_values("목표시각")
        if plot_pred.empty:
            st.info("유효한 목표시각이 없어 예측 그래프를 표시할 수 없습니다.")
        else:
            fig2 = px.line(plot_pred, x="목표시각", y=["다음온도_C", "AI예측온도_C"], title="실제 온도와 AI 예측 온도")
            st.plotly_chart(fig2)

# ★ 수정: 선택한 메뉴의 화면만 표시
if menu == "단순 예측과 성능 비교":
    st.subheader("단순 예측과 성능 비교")
    st.write("단순 예측은 현재 온도가 1시간 뒤에도 그대로 유지된다고 가정합니다. MAE는 작을수록 평균 오차가 작습니다.")
    if comparison.empty:
        st.info("현재 온도·실제 다음 온도·AI 예측 온도가 모두 있는 비교 자료가 없습니다.")
    else:
        st.dataframe(compare_table)
        st.write(comparison_message)
        st.caption("이 비교는 선택한 기록에 대한 결과이며, 다른 기간의 성능을 보장하지 않습니다.")

# ★ 수정: 선택한 메뉴의 화면만 표시
if menu == "예측 오차가 큰 기록":
    st.subheader("예측 오차가 큰 기록")

    if pred.empty:
        st.info("오차를 확인할 예측 평가 자료가 없습니다.")
    else:
        error_view = pred.copy()
        error_view["절대오차_C"] = (error_view["다음온도_C"] - error_view["AI예측온도_C"]).abs()
        error_view = error_view.sort_values("절대오차_C", ascending=False)
        show_count = st.selectbox("확인할 기록 수", [5, 10, 20], index=1)
        st.dataframe(error_view[["측정시각", "목표시각", "다음온도_C", "AI예측온도_C", "절대오차_C"]].head(show_count))
        st.caption("절대 오차가 큰 순서입니다. MAE는 평균 오차이며 개별 기록의 오차 상한이 아닙니다.")

# ★ 추가: 다른 메뉴로 이동해도 업무 메모 유지
note_key = f"saved_note_{equipment}"
note = st.session_state.get(note_key, "센서 상태와 운전 조건을 확인한 후 담당자 검토가 필요합니다.")
if menu == "업무 검토 및 저장":
    st.subheader("업무 검토 및 저장")
    note = st.text_area("확인할 사항 및 조치 제안", value=note, key=f"note_input_{equipment}")
    st.session_state[note_key] = note

report = f"""설비: {equipment}
조회 기간: {start} ~ {end}
조회 건수: {len(view)}건
AI 확인후보: {len(candidates)}건
AI 후보 비율: {rate_text} (유효 AI 판정 {ai_valid_count}건 기준)
온도 예측 MAE: {mae_text} ({len(pred)}건 비교)
{comparison_report}
업무 메모: {note}
교육용 가상 자료이며, 확인후보는 고장 확정이 아닙니다."""

if menu == "업무 검토 및 저장":
    st.text(report)

# ★ 수정: 선택한 메뉴의 화면만 표시
if menu == "파일 내려받기":
    st.subheader("파일 내려받기")
    st.caption("현재 선택한 설비와 기간의 자료를 내려받습니다. 업무 메모는 업무 검토 및 저장 화면에서 작성할 수 있습니다.")

    st.download_button("조회 결과 CSV", view.to_csv(index=False).encode("utf-8-sig"), "dashboard_result.csv")
    st.download_button("점검 후보 CSV", candidates.to_csv(index=False).encode("utf-8-sig"), "inspection_candidates.csv")
    st.download_button("보고서 TXT", report.encode("utf-8-sig"), "dashboard_report.txt")
