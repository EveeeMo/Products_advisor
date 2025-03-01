# 设置页面配置（必须是第一个Streamlit命令）
import streamlit as st
st.set_page_config(
    page_title="智能金融产品顾问",
    page_icon="🤖"
)

# 其他导入
from zhipuai import ZhipuAI
from dotenv import load_dotenv
import os
import logging
import pandas as pd
import time
import threading
from datetime import datetime, timedelta
import re  # 添加re模块导入

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 加载环境变量
load_dotenv()

# 初始化智谱AI客户端
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

# 加载产品数据
@st.cache_data
def load_products():
    try:
        df = pd.read_excel('products.xlsx')
        return df
    except Exception as e:
        logging.error(f"读取产品数据时发生错误: {str(e)}")
        return None

products_df = load_products()

def get_product_info():
    """
    获取产品信息的摘要
    """
    if products_df is None:
        return "抱歉，无法获取产品信息。"
    
    product_summary = "我们有以下类型的金融产品：\n"
    for strategy in products_df['产品策略'].unique():
        products = products_df[products_df['产品策略'] == strategy]
        product_summary += f"- {strategy}类产品 {len(products)}个，"
        product_summary += f"风险等级{','.join(products['风险级别'].unique())}，"
        product_summary += f"历史年化收益率范围{products['历史年化收益'].min():.2%}-{products['历史年化收益'].max():.2%}\n"
    
    return product_summary

def get_specific_product_info(product_name):
    """
    获取特定产品的详细信息
    """
    if products_df is None:
        return None
    
    product = products_df[products_df['产品名称'].str.contains(product_name, na=False)]
    if len(product) == 0:
        return None
    
    product = product.iloc[0]
    return {
        "产品名称": product["产品名称"],
        "产品策略": product["产品策略"],
        "风险级别": product["风险级别"],
        "封闭期": product["封闭期"],
        "历史年化收益": f"{product['历史年化收益']:.2%}",
        "起投金额": product["起投金额"],
        "赎回费": product["赎回费"] if pd.notna(product["赎回费"]) else "无",
        "产品优势": product["产品优势"]
    }

def format_product_details(product_info):
    """
    格式化产品详细信息
    """
    return f"""产品详情：
- 产品名称：{product_info['产品名称']}
- 产品策略：{product_info['产品策略']}
- 风险级别：{product_info['风险级别']}
- 封闭期：{product_info['封闭期']}
- 历史年化收益：{product_info['历史年化收益']}
- 起投金额：{product_info['起投金额']}
- 赎回费：{product_info['赎回费']}
- 产品优势：{product_info['产品优势']}"""

def is_asking_for_recommendation(query):
    """
    判断用户是否在请求产品推荐
    """
    keywords = ["推荐", "介绍", "推荐一个", "推荐一只", "有什么好的", "有哪些"]
    return any(keyword in query for keyword in keywords)

def is_user_unsatisfied(query):
    """
    判断用户是否对推荐不满意
    """
    keywords = ["不满意", "换一下", "换一个", "不合适", "不好", "不行", "其他", "别的", "重新推荐"]
    return any(keyword in query for keyword in keywords)

def update_investment_info(original_info, feedback):
    """
    根据用户反馈更新投资信息
    """
    updated_info = original_info.copy()
    
    # 提取反馈中的新信息
    feedback_info = extract_investment_info([{"content": feedback, "role": "user"}])
    
    # 更新投资信息
    for key, value in feedback_info.items():
        if value is not None:
            updated_info[key] = value
    
    return updated_info

def find_matching_products(investment_amount, expected_return, investment_period, exclude_products=None):
    """
    根据用户需求匹配合适的产品，排除已推荐过的产品
    """
    if products_df is None:
        return []
    
    if exclude_products is None:
        exclude_products = set()
    
    # 将投资金额统一转换为元
    if isinstance(investment_amount, str):
        if "万" in investment_amount:
            amount = float(investment_amount.replace("万", "")) * 10000
        else:
            amount = float(investment_amount.replace("元", ""))
    else:
        amount = float(investment_amount)
    
    # 将预期收益率转换为小数
    if isinstance(expected_return, str):
        expected_return = float(expected_return.replace("%", "")) / 100
    
    # 将投资期限转换为天数
    if isinstance(investment_period, str):
        if "年" in investment_period:
            days = int(float(investment_period.replace("年", "")) * 365)
        elif "月" in investment_period:
            days = int(float(investment_period.replace("月", "")) * 30)
        else:
            days = int(float(investment_period.replace("天", "")))
    else:
        days = int(investment_period)

    # 筛选符合条件的产品
    matching_products = []
    for _, product in products_df.iterrows():
        # 跳过已推荐过的产品
        if product['产品名称'] in exclude_products:
            continue
            
        # 检查起投金额
        min_investment = float(str(product['起投金额']).replace("元", ""))
        if amount < min_investment:
            continue
        
        # 检查收益率匹配度
        if product['历史年化收益'] < expected_return * 0.8:  # 允许20%的收益率差异
            continue
        
        # 检查投资期限
        product_period = product['封闭期']
        if isinstance(product_period, str):
            if "年" in product_period:
                product_days = int(float(product_period.replace("年", "")) * 365)
            elif "月" in product_period:
                product_days = int(float(product_period.replace("月", "")) * 30)
            else:
                product_days = int(float(product_period.replace("天", "")))
        else:
            product_days = int(product_period)
        
        if product_days > days * 1.5:  # 允许50%的期限差异
            continue
        
        # 计算匹配度分数
        score = 0
        # 收益率匹配度
        score += (1 - abs(product['历史年化收益'] - expected_return) / expected_return) * 40
        # 期限匹配度
        score += (1 - abs(product_days - days) / days) * 30
        # 起投金额匹配度
        score += (1 - (min_investment / amount if amount > min_investment else amount / min_investment)) * 30
        
        matching_products.append({
            "product": product,
            "score": score
        })
    
    # 按匹配度排序
    matching_products.sort(key=lambda x: x["score"], reverse=True)
    return matching_products[:2]  # 返回最匹配的两个产品

def extract_investment_info(messages):
    """
    从对话历史中提取投资信息
    """
    investment_info = {
        "金额": None,
        "收益": None,
        "时间": None
    }
    
    # 收益率关键词映射
    return_keywords = {
        "稳健": 0.05,  # 5%
        "保守": 0.03,  # 3%
        "激进": 0.10,  # 10%
        "高收益": 0.08,  # 8%
        "中等": 0.06   # 6%
    }
    
    # 时间关键词映射
    time_keywords = {
        "半年": "6月",
        "一年": "12月",
        "两年": "24月",
        "三年": "36月",
        "一个月": "1月",
        "三个月": "3月",
        "短期": "3月",
        "中期": "12月",
        "长期": "24月"
    }
    
    for msg in messages:
        content = msg["content"]
        
        # 提取金额
        if any(word in content for word in ["金额", "万", "元", "块", "资金"]):
            # 匹配"xx万"或"xx元"的模式
            amount_match = re.search(r'(\d+(?:\.\d+)?)\s*[万元块]', content)
            if amount_match:
                amount = amount_match.group(1)
                unit = "万" if "万" in content else "元"
                investment_info["金额"] = amount + unit
            # 匹配"xxx"的纯数字（默认为元）
            elif re.search(r'\d+(?:\.\d+)?', content):
                amount = re.search(r'\d+(?:\.\d+)?', content).group()
                investment_info["金额"] = amount + "元"
        
        # 提取收益率
        if any(word in content for word in ["收益", "%", "回报", "收益率", "以上"] + list(return_keywords.keys())):
            # 先尝试匹配"xx%以上"的模式
            rate_above_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*以上', content)
            if rate_above_match:
                rate = float(rate_above_match.group(1))
                investment_info["收益"] = str(rate)
            # 再尝试匹配具体数字
            else:
                rate_match = re.search(r'(\d+(?:\.\d+)?)\s*%', content)
                if rate_match:
                    investment_info["收益"] = rate_match.group(1)
                else:
                    # 通过关键词判断收益预期
                    for keyword, rate in return_keywords.items():
                        if keyword in content:
                            investment_info["收益"] = str(rate * 100)
                            break
        
        # 提取时间
        if any(word in content for word in ["时间", "期限", "年", "月", "天"] + list(time_keywords.keys())):
            # 先尝试匹配具体时间表达
            time_match = re.search(r'(\d+(?:\.\d+)?)\s*[年月天]', content)
            if time_match:
                period = time_match.group(0)
                investment_info["时间"] = period
            else:
                # 通过关键词判断时间
                for keyword, period in time_keywords.items():
                    if keyword in content:
                        investment_info["时间"] = period
                        break

    return investment_info

def compare_products(products):
    """
    对比两个产品的优劣，使用表格形式展示
    """
    if len(products) < 2:
        return ""
        
    product1 = products[0]["product"]
    product2 = products[1]["product"]
    
    comparison = "\n📊 产品对比分析：\n\n"
    
    # 使用表格形式展示主要指标对比
    comparison += "| 对比项目 | " + product1['产品名称'] + " | " + product2['产品名称'] + " |\n"
    comparison += "|---------|------------|------------|\n"
    
    # 收益率对比
    comparison += f"| 历史年化收益 | {product1['历史年化收益']:.2%} | {product2['历史年化收益']:.2%} |\n"
    
    # 风险等级对比
    comparison += f"| 风险等级 | {product1['风险级别']} | {product2['风险级别']} |\n"
    
    # 起投金额对比
    comparison += f"| 起投金额 | {product1['起投金额']} | {product2['起投金额']} |\n"
    
    # 封闭期对比
    comparison += f"| 封闭期 | {product1['封闭期']} | {product2['封闭期']} |\n"
    
    # 赎回规则对比
    comparison += f"| 赎回规则 | {product1['赎回费'] if pd.notna(product1['赎回费']) else '无'} | {product2['赎回费'] if pd.notna(product2['赎回费']) else '无'} |\n"
    
    # 匹配度对比
    comparison += f"| 匹配度 | {products[0]['score']:.0f}分 | {products[1]['score']:.0f}分 |\n"
    
    # 产品优势（因为可能较长，单独展示）
    comparison += "\n🌟 产品优势对比：\n"
    comparison += f"- {product1['产品名称']}：{product1['产品优势']}\n"
    comparison += f"- {product2['产品名称']}：{product2['产品优势']}\n"
    
    # 投资建议
    comparison += "\n💡 投资建议：\n"
    if products[0]["score"] > products[1]["score"]:
        comparison += f"- 主推建议：{product1['产品名称']}（匹配度：{products[0]['score']:.0f}分）\n"
        comparison += f"- 备选建议：{product2['产品名称']}（匹配度：{products[1]['score']:.0f}分）\n"
    else:
        comparison += f"- 主推建议：{product2['产品名称']}（匹配度：{products[1]['score']:.0f}分）\n"
        comparison += f"- 备选建议：{product1['产品名称']}（匹配度：{products[0]['score']:.0f}分）\n"
    
    return comparison

def generate_closing_message(products, investment_info):
    """
    生成关单话术
    """
    if not products or len(products) == 0:
        return None
        
    main_product = products[0]["product"]
    amount = investment_info["金额"]
    
    # 将金额统一转换为万元
    if "万" in amount:
        amount_value = float(amount.replace("万", ""))
    else:
        amount_value = float(amount.replace("元", "")) / 10000
        
    # 根据匹配度和风险等级建议投资比例
    if products[0]["score"] >= 85:
        recommend_ratio = 0.7  # 匹配度高，建议70%
    elif products[0]["score"] >= 75:
        recommend_ratio = 0.5  # 匹配度中等，建议50%
    else:
        recommend_ratio = 0.3  # 匹配度一般，建议30%
        
    recommend_amount = amount_value * recommend_ratio
    
    message = f"""根据您的投资需求，我强烈建议您考虑{main_product['产品名称']}。该产品{main_product['产品优势']}，完全符合您的收益预期。建议您先投入{recommend_amount:.1f}万元试水，约占您计划投资额的{recommend_ratio:.0%}。抓住当前市场机会，建议您尽快完成投资布局。"""
    
    return message

def format_recommendation(products):
    """
    格式化推荐产品信息
    """
    if not products:
        return """抱歉，根据您的需求，暂时没有找到完全匹配的产品。建议您适当调整投资条件。

您可以考虑：
1. 适当降低预期收益率
2. 调整投资期限
3. 增加投资金额

或者告诉我您可以调整的范围，我会重新为您推荐。"""
    
    result = "根据您的需求，我为您推荐以下产品：\n\n"
    for i, item in enumerate(products, 1):
        product = item["product"]
        result += f"推荐{i}：{product['产品名称']}\n"
        result += f"- 产品策略：{product['产品策略']}\n"
        result += f"- 风险等级：{product['风险级别']}\n"
        result += f"- 历史年化收益：{product['历史年化收益']:.2%}\n"
        result += f"- 起投金额：{product['起投金额']}\n"
        result += f"- 封闭期：{product['封闭期']}\n"
        result += f"- 赎回规则：{product['赎回费'] if pd.notna(product['赎回费']) else '无'}\n"
        result += f"- 产品优势：{product['产品优势']}\n"
        result += f"- 匹配度：{item['score']:.0f}分\n\n"
    
    # 添加产品对比分析
    if len(products) >= 2:
        result += compare_products(products)
    
    result += "\n⚠️ 风险提示：历史收益不代表未来收益，投资需谨慎。建议您仔细阅读产品说明书，充分了解产品特点和风险。"
    return result

def get_ai_response(messages):
    """
    获取AI的回复
    """
    try:
        # 在用户问题前添加产品信息和指导语
        if len(messages) > 0 and messages[-1]["role"] == "user":
            user_query = messages[-1]["content"]
            
            # 检查是否是表达不满意
            if is_user_unsatisfied(user_query):
                if st.session_state.last_recommendation:
                    # 构建系统提示，引导AI询问具体不满意的地方
                    system_prompt = """你是一个专业的金融产品顾问。用户对推荐的产品表示不满意。
请详细询问用户具体不满意的地方，可以从以下几个方面引导用户表达：
1. 是收益率不够高？
2. 是投资期限太长或太短？
3. 是风险等级不合适？
4. 是起投金额太高？
5. 是产品策略不符合预期？

请根据用户的具体反馈，帮助我们找到更合适的产品。"""
                    
                    messages = [{"role": "system", "content": system_prompt}] + messages
                    response = client.chat.completions.create(
                        model="glm-4-0520",
                        messages=messages,
                        stream=False
                    )
                    return response.choices[0].message.content
                else:
                    return "抱歉，我没有找到之前的推荐记录。请重新告诉我您的投资需求，我会为您推荐合适的产品。"
            
            product_info = get_product_info()
            
            # 检查是否在询问具体产品
            specific_product = None
            for product_name in products_df['产品名称']:
                if product_name in user_query:
                    specific_product = get_specific_product_info(product_name)
                    break
            
            if specific_product:
                product_details = format_product_details(specific_product)
                system_prompt = f"""你是一个专业的金融产品顾问。用户询问的产品具体信息如下：

{product_details}

请根据这些信息回答用户的问题，解释产品特点和风险。请注意：
1. 重点解释产品的优势和特点
2. 说明风险等级和适合的投资者类型
3. 解释封闭期和赎回规则
4. 分析历史收益情况
5. 提供专业的投资建议
"""
            elif is_asking_for_recommendation(user_query):
                # 直接返回三个问题，不经过大模型处理
                return """为了给您推荐最合适的产品，请告诉我：

1. 您计划投资的金额是多少？
2. 您的预期收益率是？
3. 您的投资时间是？"""
            else:
                # 从对话历史中提取投资信息
                investment_info = extract_investment_info(messages)
                
                # 如果有上一次推荐记录，并且用户提供了新的反馈
                if st.session_state.last_recommendation and len(messages) >= 2:
                    # 更新投资信息
                    updated_info = update_investment_info(
                        st.session_state.last_recommendation["investment_info"],
                        user_query
                    )
                    
                    # 获取已推荐过的产品
                    exclude_products = st.session_state.recommended_products
                    
                    # 查找新的匹配产品
                    matching_products = find_matching_products(
                        updated_info["金额"],
                        updated_info["收益"],
                        updated_info["时间"],
                        exclude_products
                    )
                    
                    # 更新已推荐产品集合
                    for item in matching_products:
                        exclude_products.add(item["product"]["产品名称"])
                    
                    # 保存当前推荐的产品和投资信息到会话状态
                    st.session_state.last_recommendation = {
                        "products": matching_products,
                        "investment_info": updated_info,
                        "timestamp": time.time()
                    }
                    st.session_state.recommended_products = exclude_products
                    
                    return format_recommendation(matching_products)
                
                # 如果已经收集到所有信息，则进行产品推荐
                if all(investment_info.values()):
                    # 查找匹配的产品
                    matching_products = find_matching_products(
                        investment_info["金额"],
                        investment_info["收益"],
                        investment_info["时间"],
                        st.session_state.recommended_products
                    )
                    
                    # 更新已推荐产品集合
                    for item in matching_products:
                        st.session_state.recommended_products.add(item["product"]["产品名称"])
                    
                    # 保存当前推荐的产品和投资信息到会话状态
                    st.session_state.last_recommendation = {
                        "products": matching_products,
                        "investment_info": investment_info,
                        "timestamp": time.time()
                    }
                    return format_recommendation(matching_products)
                else:
                    # 如果信息不完整，继续询问缺失的信息
                    missing_info = []
                    if not investment_info["金额"]:
                        missing_info.append("您计划投资的金额是多少？")
                    if not investment_info["收益"]:
                        missing_info.append("您的预期收益率是？")
                    if not investment_info["时间"]:
                        missing_info.append("您的投资时间是？")
                    
                    return "\n".join(missing_info)

            messages = [{"role": "system", "content": system_prompt}] + messages

        response = client.chat.completions.create(
            model="glm-4-0520",
            messages=messages,
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"调用智谱AI API时发生错误: {str(e)}")
        return "抱歉，我现在遇到了一些问题，请稍后再试。"

# 设置页面标题
st.title("智能金融产品顾问 🤖")
st.caption("Powered by 智谱AI GLM-4")

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_recommendation" not in st.session_state:
    st.session_state.last_recommendation = None
if "last_closing_time" not in st.session_state:
    st.session_state.last_closing_time = None
if "recommended_products" not in st.session_state:
    st.session_state.recommended_products = set()  # 用于存储已推荐过的产品名称

# 显示产品统计信息
if products_df is not None:
    with st.expander("查看产品概况"):
        st.write(get_product_info())
        st.write("\n### 所有产品列表：")
        for name in products_df['产品名称']:
            st.write(f"- {name}")

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 用户输入
if prompt := st.chat_input("请描述您的投资需求..."):
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 显示AI思考中的状态
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                # 获取AI回复
                messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
                
                # 检查是否是对之前推荐的不满意表达
                if is_user_unsatisfied(prompt):
                    # 查找最近的推荐消息
                    last_recommendation = None
                    for i in range(len(st.session_state.messages)-2, -1, -1):
                        if "推荐" in st.session_state.messages[i]["content"] and st.session_state.messages[i]["role"] == "assistant":
                            last_recommendation = st.session_state.messages[i]["content"]
                            break
                    
                    if last_recommendation:
                        # 构建系统提示，引导AI询问具体不满意的地方
                        system_prompt = f"""你是一个专业的金融产品顾问。用户对以下推荐的产品表示不满意：

{last_recommendation}

请详细询问用户具体不满意的地方，可以从以下几个方面引导用户表达：
1. 是收益率不够高？
2. 是投资期限太长或太短？
3. 是风险等级不合适？
4. 是起投金额太高？
5. 是产品策略不符合预期？

请根据用户的具体反馈，帮助我们找到更合适的产品。"""
                        
                        messages = [{"role": "system", "content": system_prompt}] + messages[-2:]
                        response = client.chat.completions.create(
                            model="glm-4-0520",
                            messages=messages,
                            stream=False
                        )
                        response = response.choices[0].message.content
                    else:
                        response = "抱歉，我没有找到之前的推荐记录。请重新告诉我您的投资需求，我会为您推荐合适的产品。"
                else:
                    response = get_ai_response(messages)
                
                # 添加AI回复到历史记录
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.markdown(response)
                
                # 如果是产品推荐，等待10秒后发送关单消息
                if "推荐以下产品" in response:
                    time.sleep(10)
                    
                    # 从对话历史中提取投资信息
                    investment_info = extract_investment_info(messages)
                    
                    # 发送关单消息
                    closing_message = generate_closing_message(
                        st.session_state.last_recommendation["products"] if st.session_state.last_recommendation else None,
                        investment_info
                    )
                    
                    if closing_message:
                        st.session_state.messages.append({"role": "assistant", "content": closing_message})
                        st.session_state.last_closing_time = time.time()
                        st.rerun()
                    
            except Exception as e:
                logging.error(f"处理用户输入时发生错误: {str(e)}")
                st.error("抱歉，处理您的请求时发生错误，请重试。") 