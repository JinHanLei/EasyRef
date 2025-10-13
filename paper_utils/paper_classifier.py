import pandas as pd
from tqdm import tqdm
import openai


client = openai.OpenAI(
    api_key="None",
    base_url="http://10.8.27.22:30000/v1"
)


def query_builder(title, abstract):
    return "title: '{}'\nabstract: '{}'\n".format(title, abstract)


def classify_papers(test, train, task, prompt):
    if not task in test.columns:
        test[task] = None
    history = [{"role": "system", "content": prompt}]
    if train is not None:
        for i in range(len(train)):
            history += ([{"role": "user", "content": query_builder(train["title"][i], train["abstract"][i])},
                         {"role": "assistant", "content": str(train[task][i])}])
    for i in tqdm(range(len(test))):
        if pd.isna(test[task][i]):
            try:
                messages = history + [{"role": "user", "content": query_builder(test["title"][i], test["abstract"][i])}]
                chat = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
                label = chat.choices[0].message.content
            except Exception as e:
                label = None
                print(e)
            test.loc[i, task] = label
    return test


if __name__ == '__main__':

    PREFIX = "You are an expert in NLP. Please classify the article according to its title and abstract. "
    PROMPT = {
        "is_evaluate": """Please classify the following article as evaluation metric or not. Please classify according to the following requirements:
        1. This paper must include newly designed evaluation indicators. If only existing evaluation metrics are used, it does not count.
        2. The evaluation metrics need to be designed based on large language models. If it is a statistical metric like ROUGE, it does not count.
        3. It needs to be related to automatic text summarization. If it is from other fields such as text generation, it does not count.
        Mark those that meet the above conditions as 1 and those that do not as 0.""",
        # "task": "The task include test, survey, dataset, model, etc. ",
        # "methodology": "The methodologies include template, Cot, Agent, RAG, fine-tuning, training, distillation, etc. ",
        # "domain": "If no specific domain is specified and it only indicates summarization task, then mark it as general. If specific fields are mentioned, including medical, dialogue, law, news, etc., please indicate the domain name. ",
        # "dataset": "Please list all the datasets used in this paper. If not found, please output 0"
    }
    SUFFIX = "No need for explanation."


    sum_test = pd.read_csv("data/evaluation_summarization_llm_all.csv")
    # sum_train = pd.read_csv(f"data/LLM_train.csv")
    for task in PROMPT:
        prompt = PREFIX + PROMPT[task] + SUFFIX
        sum_test = classify_papers(sum_test, None, task, prompt)

    # for task in PROMPT:
    #     prompt = PREFIX + PROMPT[task] + SUFFIX
    #     if task not in sum_train.columns:
    #         prompt += f"Just output {task}. "
    #         sum_test = classify_papers(sum_test, None, task, prompt)
    #     else:
    #         sum_test = classify_papers(sum_test, sum_train, task, prompt)
    sum_test.to_csv("data/evaluation_summarization_llm_all.csv", index=False)
