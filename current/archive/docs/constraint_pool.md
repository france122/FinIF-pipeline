=== HARD CHECKERS (26 个) ===
ID                             | Tag  | 描述/text_hint                             | 参数化
--------------------------------------------------------------------------------------------------------------
check_word_range               | N1   | 控制在{min_words}到{max_words}字              | ✓ 
check_word_limit               | N1   | 不超过{max_words}字                          | ✓ 
check_sentence_count           | N2   | 至少{min_count}个完整句子                       | ✓ 
check_paragraph_count          | N2   | 分为{min_count}到{max_count}个段落             | ✓ 
check_section_count            | F1   | 至少{min_sections}个独立章节                    | ✓ 
check_heading_level            | F1   | {min_count}个{level}级标题                   | ✓ 
check_heading_depth            | F1   | 使用至少{min_depth}层标题层级                     | ✓ 
check_ordered_list_count       | F2   | {min_count}到{max_count}条有序列表             | ✓ 
check_markdown_table           | F3   | 使用Markdown表格展示数据                         | ✗ 
check_blockquote_count         | F5   | 至少{min_count}处引用块                        | ✓ 
check_first_last_line          | F6   | 首行包含"{first_line}"，末行包含"{last_line}"     | ✓ 
check_no_table                 | F3   | 不使用表格                                    | ✗ (逆向)
check_no_list                  | F2   | 不使用列表                                    | ✗ (逆向)
check_forbidden_pattern        | L2   | 不使用{forbidden_desc}                      | ✓ 
check_first_word               | F6   | 开头第一个词必须是"{word}"                        | ✓ 
check_first_person             | L2   | 第一人称叙事                                   | ✓ (逆向)
check_first_line_format        | F6   | 首行用加粗文字                                  | ✓ 
check_keyword_presence         | L1   | 必须包含"{kw1}"和"{kw2}"                      | ✓ 
check_json_format              | F4   | JSON格式输出                                 | ✗ 
check_checkbox_format          | F7   | Checkbox格式标记事项                           | ✗ 
check_risk_disclaimer          | L1   | 末尾风险提示声明                                 | ✓ 
check_conditional_trigger      | C5   | 若提到{trigger}必须说明{followup}               | ✓ 
check_decimal_places           | N3   | 数值保留{places}位小数                          | ✓ 
check_currency_format          | L4   | 金额统一使用{unit}为单位                          | ✓ 
check_no_percent               | L4   | 不使用百分号，用文字表达百分比                          | ✗ (逆向)
check_no_arabic_numerals       | L2   | 不使用阿拉伯数字，用中文大写                           | ✗ (逆向)

=== SOFT TEMPLATES (25 个) ===
ID       | Tag  | 描述
----------------------------------------------------------------------
GS-1     | F6   | 先给出结论，再展开分析过程
GS-2     | F6   | 回答末尾必须包含一段总结
GS-3     | S1   | 使用正式书面语，不得口语化
GS-4     | S1   | 语气客观中立，不包含主观投资建议
GS-5     | S3   | 段落间逻辑连贯，有明确过渡
GS-7     | S4   | 使用类比或举例来辅助解释
GS-8a    | S2   | 以普通投资者能理解的方式撰写
GS-8b    | S2   | 以机构投资者为目标读者撰写
GS-9a    | S2   | 以专业分析师的口吻撰写
GS-9b    | S1   | 以谨慎保守的语气撰写
FS-1     | C3   | 从ESG（环境、社会、治理）角度进行评价
FS-3     | L3   | 专业术语英文缩写需给出中文全称
FS-6     | C3   | 从风险管理的角度分析
FS-7     | S2   | 站在监管机构的立场回答
FS-8     | S2   | 从零售投资者的视角分析
FS-9     | C3   | 从宏观经济的角度分析
FS-10    | L3   | 使用通俗语言，避免专业术语和行话
FS-13    | L3   | 不得使用金融术语英文缩写（如ROE/PE/EBITDA等）
FS-14    | C3   | 从产业链/供应链角度分析
FS-15    | C3   | 从估值与定价角度分析
FS-16    | S2   | 以信用评级分析师的视角撰写
GS-10    | S4   | 正反两面对比论述（优势vs劣势/机会vs风险）
GS-11    | S1   | 简洁干练，避免冗余修饰
GS-12    | F6   | 按重要性/影响程度从大到小排列
GS-13    | S3   | 数据驱动论述，每个论点用数据佐证