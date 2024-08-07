from toolbox import update_ui
from toolbox import CatchException, report_exception
from .crazy_utils import parse_pdf
from .crazy_utils import request_gpt_model_in_new_thread_with_ui_alive

fast_debug = True

@CatchException
def 金句提取Gateway(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    import glob, os

    print(f'llm_kwargs: {llm_kwargs}')
    # 基本信息：功能、贡献者
    chatbot.append([
        "函数插件功能？",
        "从文章/书籍中提取金句，并且将结合上下文内容，进行学术解答。函数插件贡献者: chentao"])
        # "理解PDF论文内容，并且将结合上下文内容，进行学术解答。函数插件贡献者: Hanzoe, binary-husky"])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 尝试导入依赖，如果缺少依赖，则给出安装建议
    try:
        import fitz
    except:
        report_exception(chatbot, history,
            a = f"解析项目: {txt}",
            b = f"导入软件依赖失败。使用该模块需要额外依赖，安装方法```pip install --upgrade pymupdf```。")
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return

    print(txt)
    print(history)

    # # 清空历史，以免输入溢出
    history = []
    # history.append('执行完毕')
    # chatbot.append(["i_say_show_user", "执行完毕"])
    # time.sleep(0.5)
    # yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 检测输入参数，如没有给定输入参数，直接退出
    if os.path.exists(txt):
        project_folder = txt
    else:
        if txt == "":
            txt = '空空如也的输入栏'
        report_exception(chatbot, history,
                         a=f"解析项目: {txt}", b=f"找不到本地项目或无权访问: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    # 搜索需要处理的文件清单
    file_manifest = [f for f in glob.glob(f'{project_folder}/**/*.pdf', recursive=True)]
    # 如果没找到任何文件
    if len(file_manifest) == 0:
        report_exception(chatbot, history,
                         a=f"解析项目: {txt}", b=f"找不到任何.tex或.pdf文件: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return
    txt = file_manifest[0]

    print('file_manifest', txt)
    paper_fragments = parse_pdf(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt)
    n_fragment = len(paper_fragments)
    MAX_WORD_TOTAL = 4096
    iteration_results = []

    ############################## <第 1 步，从摘要中提取高价值信息，放到history中> ##################################
    final_results = []
    last_iteration_result = ""  # 初始值是摘要

    prompt_tpl = """金句通常指的是文章、书籍、演讲或电影中那些富有哲理、引人深思或具有强烈感染力的句子。它们往往因为其深刻的含义、独特的表达方式或在特定情境下的恰当使用而被人们所铭记。下面我将给你一段用一对符号'''标记出来文本，请为我找出里面的金句，不要找人物或场景描述相关的内容，如果没有符合条件的金句，那么请直接回复：没有找到符合条件的金句；如果有多句，请用规定的格式列举出来。
- 金句的条件：启发智慧；富有哲理；为人处世；引人深思；内容完整；揭露本质、规律、人性、思想；内容完整
- 格式： 使用符合json格式的输出返回，格式举例：
[
{
  "text": "这里是金句内容",
  "comment": "这里是分析或者评论",
  "score": "这里是符合金句条件的评分，满分100分"
}
]

'''%s'''
"""

#     prompt_tpl = """金句通常指的是文章、书籍、演讲或电影中那些富有哲理、引人深思或具有强烈感染力的句子。它们往往因为其深刻的含义、独特的表达方式或在特定情境下的恰当使用而被人们所铭记。下面我将给你一段用一对符号'''标记出来文本，请为我找出里面的金句，不要找人物或场景描述相关的内容，如果没有符合条件的金句，那么请直接回复：没有找到符合条件的金句；如果有多句，请用规定的格式列举出来。
# - 金句的条件：启发智慧；富有哲理；为人处世；引人深思；内容完整；揭露本质、规律、人性、思想；内容完整
# - 格式： 使用符合markdown格式的输出返回，格式举例：
# ***
# * 文本：这里是金句内容
# * 分析：这里是分析或者评论
# * 评分：这里是符合金句条件的评分，满分100分
# ***
#
# '''%s'''
# """

    #   "labels": "金句的标签，用分号隔开，如：哲学;成长;人性;心理;规律;思想;社会;财富;军事; 等等"

    n_fragment = 3
    for i in range(n_fragment):
        # i_say = f"Read this section, recapitulate the content of this section with less than {NUM_OF_WORD} words: {paper_fragments[i]}"
        i_say = prompt_tpl % paper_fragments[i]
        print('==' * 20, ' length: ', len(paper_fragments[i]))
        print(i_say)
        print('==' * 20)
        i_say_show_user = f"[{i+1}/{n_fragment}] 阅读本段内容, 提取文中的金句: {paper_fragments[i][:200]} ...."
        gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(i_say, i_say_show_user,  # i_say=真正给chatgpt的提问， i_say_show_user=给用户看的提问
                                                                           llm_kwargs, chatbot,
                                                                           # history=["The main idea of the previous section is?", last_iteration_result], # 迭代上一次的结果
                                                                           history=[], # 迭代上一次的结果
                                                                           sys_prompt="阅读本段内容, 提取文中的金句。"  # 提示
                                                                        )
        iteration_results.append(gpt_say)
        last_iteration_result = gpt_say

    final_results.extend(iteration_results)
    yield from update_ui(chatbot=chatbot, history=final_results) # 注意这里的历史记录被替代了

    # # 检测输入参数，如没有给定输入参数，直接退出
    # if os.path.exists(txt):
    #     project_folder = txt
    # else:
    #     if txt == "":
    #         txt = '空空如也的输入栏'
    #     report_exception(chatbot, history,
    #                      a=f"解析项目: {txt}", b=f"找不到本地项目或无权访问: {txt}")
    #     yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
    #     return
    #
    # # 搜索需要处理的文件清单
    # file_manifest = [f for f in glob.glob(f'{project_folder}/**/*.pdf', recursive=True)]
    # # 如果没找到任何文件
    # if len(file_manifest) == 0:
    #     report_exception(chatbot, history,
    #                      a=f"解析项目: {txt}", b=f"找不到任何.tex或.pdf文件: {txt}")
    #     yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
    #     return
    # txt = file_manifest[0]
    # # 开始正式执行任务
    # yield from 解析PDF(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt)
