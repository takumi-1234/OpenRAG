# frontend-streamlit/app/streamlit_app.py

import streamlit as st
from requests.exceptions import HTTPError
import logging

from api_client import go_api, python_rag_api

# --- ページ設定 & 初期化 ---
st.set_page_config(page_title="OpenRAG", layout="wide")
logging.basicConfig(level=logging.INFO)

# --- セッション状態の初期化 ---
def init_session_state():
    defaults = {
        "token": None,
        "user_info": None,
        "lectures": [],
        "selected_lecture": None,
        "messages": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- 認証ページ ---
def login_page():
    st.header("ログイン")
    with st.form("login_form"):
        email = st.text_input("メールアドレス")
        password = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン")

        if submitted:
            if not email or not password:
                st.error("メールアドレスとパスワードを入力してください。")
                return

            try:
                with st.spinner("ログイン中..."):
                    login_data = go_api.login(email, password)
                    st.session_state.token = login_data.get("token")
                    st.session_state.user_info = login_data.get("user")
                    st.rerun()  # ログイン成功後、ページを再読み込みしてメインページへ
            except HTTPError as e:
                if e.response.status_code == 401:
                    st.error("メールアドレスまたはパスワードが正しくありません。")
                else:
                    st.error(f"ログイン中にエラーが発生しました: {e.response.text}")
            except Exception as e:
                st.error(f"予期せぬエラーが発生しました: {e}")

# --- メインページ ---
def main_page():
    # --- サイドバー ---
    with st.sidebar:
        st.title("📚 OpenRAG")
        if st.session_state.user_info:
            st.write(f"ようこそ、 **{st.session_state.user_info['username']}** さん")
        
        if st.button("ログアウト"):
            # セッション状態をクリアして再実行
            for key in st.session_state.keys():
                del st.session_state[key]
            init_session_state()
            st.rerun()

        st.divider()

        # 講義リストの取得と選択
        try:
            st.session_state.lectures = go_api.get_lectures(st.session_state.token)
        except Exception as e:
            st.error(f"講義リストの取得に失敗しました: {e}")
            return
        
        if st.session_state.lectures:
            lecture_options = {lec['id']: lec['name'] for lec in st.session_state.lectures}
            selected_id = st.selectbox(
                "講義を選択してください",
                options=list(lecture_options.keys()),
                format_func=lambda x: lecture_options[x],
                index=0 if not st.session_state.selected_lecture else list(lecture_options.keys()).index(st.session_state.selected_lecture['id'])
            )
            # 選択された講義オブジェクトを保存
            if not st.session_state.selected_lecture or st.session_state.selected_lecture['id'] != selected_id:
                st.session_state.selected_lecture = next((lec for lec in st.session_state.lectures if lec['id'] == selected_id), None)
                st.session_state.messages = [] # 講義を切り替えたらチャット履歴をリセット
                st.rerun()
        else:
            st.warning("履修中の講義がありません。")
            st.session_state.selected_lecture = None
        
        st.divider()

        # ファイルアップロード
        if st.session_state.selected_lecture:
            with st.expander("資料をアップロード"):
                uploaded_file = st.file_uploader("PDF, DOCX, TXTファイルをアップロード", type=["pdf", "docx", "txt"])
                if uploaded_file:
                    if st.button("ファイルを処理"):
                        with st.spinner(f"「{st.session_state.selected_lecture['name']}」にファイルをアップロード中..."):
                            try:
                                result = python_rag_api.upload_document(
                                    token=st.session_state.token,
                                    lecture_id=st.session_state.selected_lecture['id'],
                                    file=uploaded_file
                                )
                                st.success(f"ファイル「{result['filename']}」の処理が完了しました。")
                            except Exception as e:
                                st.error(f"アップロードに失敗しました: {e}")
    
    # --- メインコンテンツ ---
    if not st.session_state.selected_lecture:
        st.info("サイドバーから講義を選択してください。")
        return

    st.header(f"💬 {st.session_state.selected_lecture['name']}")

    # チャット履歴の表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザー入力
    if prompt := st.chat_input("質問を入力してください..."):
        # ユーザーメッセージを履歴に追加して表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # アシスタントの応答処理
        with st.chat_message("assistant"):
            with st.spinner("回答を生成中です..."):
                try:
                    response_data = python_rag_api.post_chat_message(
                        token=st.session_state.token,
                        lecture_id=st.session_state.selected_lecture['id'],
                        query=prompt,
                        system_prompt=st.session_state.selected_lecture.get("system_prompt")
                    )
                    
                    response_text = response_data.get("response", "回答を取得できませんでした。")
                    sources = response_data.get("sources", [])
                    
                    full_response = response_text
                    if sources:
                        sources_str = "\n- ".join(sorted(list(set(sources))))
                        full_response += f"\n\n---\n**参照ソース:**\n- {sources_str}"

                    st.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

                except Exception as e:
                    error_msg = f"回答の生成中にエラーが発生しました: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


# --- メインロジック (ページの切り替え) ---
if st.session_state.token:
    main_page()
else:
    login_page()