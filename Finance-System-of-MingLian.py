import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from models import Session, Record


CSV_FILE = "MLJY_records.csv"

# 获取当前密码
def get_password():
    password = os.getenv("MLJY_PASSWORD")  # 从环境变量中获取密码
    print(f"Debug: Retrieved password from environment variable.")  # 调试信息
    return password  # 返回密码

ORIGINAL_PASSWORD = get_password()  # 使用新的获取密码方法

# 初始化 CSV 文件（如果文件不存在）
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=['学生姓名', '操作类型', '课程名称', '金额', '备注']).to_csv(CSV_FILE, index=False)

# 创建数据库引擎
engine = create_engine('sqlite:///MLJY_records.db')
Base = declarative_base()

class Record(Base):
    __tablename__ = 'records'
    
    id = Column(String, primary_key=True)
    name = Column(String)
    operation = Column(String)
    item = Column(String)
    amount = Column(Float)
    remarks = Column(Text)

Base.metadata.create_all(engine)

# 创建会话
Session = sessionmaker(bind=engine)

# 从数据库加载数据
def load_data():
    session = Session()
    records = session.query(Record).all()
    return pd.DataFrame([(r.name, r.operation, r.item, r.amount, r.remarks, r.category) for r in records],
                        columns=['学生姓名', '操作类型', '课程名称', '金额', '备注']) 

# 将数据保存到数据库
def save_data(df):
    session = Session()
    # 清空表格
    session.query(Record).delete()
    for index, row in df.iterrows():
        record = Record(
            id=str(index),  # 或者使用其他唯一标识符
            name=row['学生姓名'],
            operation=row['操作类型'],
            item=row['课程名称'],
            amount=row['金额'],
            remarks=row['备注'],
        )
        session.add(record)
    session.commit()

# 导出数据为 Excel 文件
def export_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="上传记录")
    output.seek(0)
    return output

# 设置新密码
def set_password(new_password):
    # 这里可以考虑将新密码存储到环境变量中，但需要注意环境变量在运行时不能直接更改
    pass  # 需要实现更新环境变量的逻辑

# 页面1: 输入界面
def input_page():
    st.title("名联教育财务系统")
    
    # 初始化会话状态
    if 'show_edit_form' not in st.session_state:
        st.session_state.show_edit_form = False
    if 'edit_record_index' not in st.session_state:
        st.session_state.edit_record_index = None

    with st.form("input_form"):
        name = st.text_input("学生姓名", key="surname_input")
        selected_operation = st.radio(
            "选择操作类型",
            options=["初次缴费", "补充缴费", "退费"],
            key="operation_radio",
            horizontal=True
        )
        item = st.text_input("课程名称")
        amount = st.number_input("金额", min_value=0.0, format="%.2f")
        remarks = st.text_area("备注", "", key="remarks_input")
        submitted = st.form_submit_button("提交")
        
        if submitted:
            if not name or not item:
                st.error("学生姓名和课程名称不能为空！")
            elif amount <= 0:
                st.error("金额必须大于0！")
            else:
                df = load_data()
                existing_record = df[(df['学生姓名'] == name) & (df['课程名称'] == item) & (df['操作类型'] == selected_operation)]

                if not existing_record.empty:
                    st.warning("该人员此课程的缴费记录已经存在！")
                    st.session_state.show_edit_form = True
                    st.session_state.edit_record_index = existing_record.index[0]
                else:
                    # 新增记录
                    new_record = pd.DataFrame([[name, selected_operation, item, amount, remarks]], 
                                           columns=['学生姓名', '操作类型', '课程名称', '金额', '备注'])
                    df = pd.concat([df, new_record], ignore_index=True)
                    save_data(df)
                    st.success("上传记录已添加！")

    if st.session_state.show_edit_form:
        st.write("修改金额：")
        with st.form("edit_form"):
            df = load_data()
            record_index = st.session_state.edit_record_index
            new_amount = st.number_input("修改金额", value=df.loc[record_index, '金额'], min_value=0.0, format="%.2f")
            new_remarks = st.text_area("新增备注", key="edit_remarks_input")
            submit_button = st.form_submit_button("保存修改")
            if submit_button:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                modified_note = f"已修改{current_time}，{new_remarks}"
                if df.loc[record_index, '备注']:
                    df.loc[record_index, '备注'] += " 丨 " + modified_note
                else:
                    df.loc[record_index, '备注'] = modified_note

                df.loc[record_index, '金额'] = new_amount
                df.loc[record_index, '备注'] = df.loc[record_index, '备注']
                save_data(df)
                st.success("金额已修改！")
                st.session_state.show_edit_form = False
                st.session_state.edit_record_index = None

# 页面2: 明细页面（需要密码）
def details_page():
    st.title("账本管理中心")
    
    password = st.text_input("请输入密码", type="password")
    if st.button("验证密码"):
        if password == get_password():
            st.session_state["authenticated"] = True
            st.success("密码正确！")
        else:
            st.error("密码错误，无法访问！")
            print(f"Debug: Input password: {password}")  # 调试信息
    
    if st.session_state.get("authenticated", False):
        df = load_data()
        st.write("所有上传明细：")
        st.dataframe(df)

        # 删除记录功能
        record_to_delete = st.selectbox("选择要删除的记录", df.index, format_func=lambda x: f"{df.loc[x, '学生姓名']} - {df.loc[x, '课程名称']}")
        if st.button("删除记录"):
            if st.session_state.get("authenticated", False):
                # 从数据库中删除记录
                session = Session()
                session.query(Record).filter(Record.id == str(record_to_delete)).delete()
                session.commit()
                
                # 从 CSV 文件中删除记录
                df = df.drop(record_to_delete).reset_index(drop=True)
                # df.to_csv(CSV_FILE, index=False)  # 删除CSV文件保存
                
                st.success("记录已删除！")
            else:
                st.error("请先验证密码！")

        st.write("### 筛选")
        if 'filter_type' not in st.session_state:
            st.session_state.filter_type = None
        if 'show_filter' not in st.session_state:
            st.session_state.show_filter = False

        filter_choice = st.radio(
            "选择筛选方式",
            ["按课程名称筛选", "按学生姓名筛选", "按操作类型筛选"],
            key="filter_radio"
        )

        if filter_choice == "按操作类型筛选":
            operations = df["操作类型"].unique()
            selected_value = st.selectbox("选择操作类型", operations)
            
            if st.button("确定筛选", key="confirm_filter"):
                filtered_df = df[df["操作类型"] == selected_value]
                st.write(f"显示 {selected_value} 操作类型的上传记录：")
                st.dataframe(filtered_df)

        elif filter_choice == "按课程名称筛选":
            payment_projects = df["课程名称"].unique()
            selected_value = st.selectbox("选择课程名称", payment_projects)
            
            if st.button("确定筛选", key="confirm_filter"):
                filtered_df = df[df["课程名称"] == selected_value]
                st.write(f"显示 {selected_value} 的上传记录：")
                st.dataframe(filtered_df)

        elif filter_choice == "按学生姓名筛选":
            customer_names = df["学生姓名"].unique()
            selected_value = st.radio("选择学生姓名", customer_names)
            
            if st.button("确定筛选", key="confirm_filter"):
                filtered_df = df[df["学生姓名"] == selected_value]
                st.write(f"显示学生姓名为 {selected_value} 的上传记录：")
                st.dataframe(filtered_df)

        default_name = f"records_{datetime.now().strftime('%Y%m%d_%H%M')}"
        file_name = st.text_input("请输入导出文件名", value=default_name)
        if st.button("导出为 Excel 文件"):
            if not file_name:
                st.warning("请输入文件名！")
            else:
                excel_file = export_to_excel(df)
                st.download_button(
                    label="下载 Excel 文件",
                    data=excel_file,
                    file_name=f"{file_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# 页面3: 查询材料上传历史
def query_page():
    st.title("按姓名查询缴费记录")
    
    name_to_query = st.text_input("请输入学生姓名")
    if st.button("查询"):
        df = load_data()
        result = df[df['学生姓名'] == name_to_query]
        if not result.empty:
            st.write(f"{name_to_query} 的上传记录：")
            st.dataframe(result)
        else:
            st.warning("未找到其上传记录。")

# 页面4: 密码设置页面
def password_page():
    st.title("密码设置页面")
    
    current_password = st.text_input("请输入当前密码", type="password")
    new_password = st.text_input("请输入新密码", type="password")
    confirm_password = st.text_input("请确认新密码", type="password")
    
    if st.button("设置新密码"):
        if current_password != get_password():
            st.error("当前密码错误！")
        elif new_password != confirm_password:
            st.error("新密码与确认密码不一致！")
        else:
            set_password(new_password)
            st.success("密码已更新！")

# 主页面导航
st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["输入界面", "账本中心", "查询材料上传历史", "密码设置页面"])

if page == "输入界面":
    input_page()
elif page == "账本中心":
    details_page()
elif page == "查询材料上传历史":
    query_page()
elif page == "密码设置页面":
    password_page()