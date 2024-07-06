import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from multiprocessing import Pool

user_agent = UserAgent()


headers = {'user-agent': user_agent.chrome}

filter_map = {
    "не имеет значения": "",
    "от 1 года до 3 лет": "&experience=between1And3",
    "нет опыта": "&experience=noExperience",
    "полный день": "&schedule=fullDay",
    "сменный график": "&schedule=shift",
    "вахтовый метод": "&schedule=flyInFlyOut",
    "удаленная работа": "&schedule=remote",
    "гибкий график": "&schedule=flexible",
    "не требуется или не указано": "&education=not_required_or_not_specified",
    "среднее профессиональное": "&education=special_secondary",
    "среднее": "&education_level=secondary",
    "среднее специальное": "&education_level=special_secondary",
    "незаконченное высшее": "&education_level=unfinished_higher",
    "бакалавр": "&education_level=bachelor",
    "магистр": "&education_level=master",
    "кандидат наук": "&education_level=candidate",
    "доктор наук": "&education_level=doctor",
    "высшее": ""
}

def fetch_vacancy_info(url):
    vacancies = []
    response = requests.get(url=url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    vacancy_elements = soup.find_all(class_='vacancy-card--z_UXteNo7bRGzxWVcL7y font-inter')

    for element in vacancy_elements:
        name = element.find(attrs={'data-qa': 'bloko-header-2'}).text
        link = element.find("a", class_="bloko-link")["href"]
        compensation = element.find(class_="compensation-labels--uUto71l5gcnhU2I8TZmz")
        salary = compensation.find("span", class_="bloko-text").text if compensation.find("span", "bloko-text") else ""
        experience = compensation.find(attrs={'data-qa': 'vacancy-serp__vacancy-work-experience'}).text if compensation.find(
            attrs={'data-qa': 'vacancy-serp__vacancy-work-experience'}) else ""
        company = element.find(attrs={'data-qa': 'vacancy-serp__vacancy-employer'}).text if element.find(
            attrs={'data-qa': 'vacancy-serp__vacancy-employer'}) else ""
        city = element.find(attrs={'data-qa': 'vacancy-serp__vacancy-address_narrow'}).text if element.find(
            attrs={'data-qa': 'vacancy-serp__vacancy-address_narrow'}) else ""
        vacancies.append((name, link, salary, company, city, experience))
    return vacancies

def fetch_resume_info(url):
    resumes = []
    response = requests.get(url=url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    resume_elements = soup.find_all(attrs={'data-qa': 'resume-serp__resume'})

    for element in resume_elements:
        name = element.find("h3", class_="bloko-header-section-3").text
        link = "https://hh.ru" + element.find("a", class_="bloko-link")["href"]
        experience_element = element.find(attrs={'data-qa': 'resume-serp__resume-excpirience-sum'})
        status_element = element.find(class_="tag_job-search-status-active--WAZ6Sx3vDygvcdzNm06h")
        age = element.find(attrs={'data-qa': 'resume-serp__resume-age'}).text.replace('\xa0', " ") if element.find(
            attrs={'data-qa': 'resume-serp__resume-age'}) else ""
        experience = experience_element.text.replace('\xa0', " ") if experience_element else ""
        status = status_element.text if status_element else ""
        resumes.append((name, link, age, experience, status))
    return resumes

def collect_vacancies(query, filters):
    filter_string = ""
    if "высшее" in filters.values():
        filter_string += "&education=higher"
    for key in filters.values():
        filter_string += filter_map[key]

    main_url = f"https://hh.ru/search/vacancy?text={query}&salary=&ored_clusters=true&page=0" + filter_string
    response = requests.get(url=main_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    pager = soup.find_all(class_="pager-item-not-in-short-range")
    num_pages = int(pager[-1].text)

    urls = [f"https://hh.ru/search/vacancy?text={query}&salary=&ored_clusters=true&page={page}" + filter_string for page in range(num_pages)]
    with Pool(5) as p:
        vacancy_groups = p.map(fetch_vacancy_info, urls)

    all_vacancies = [vacancy for group in vacancy_groups for vacancy in group]
    total_vacancies_text = soup.find(attrs={'data-qa': 'bloko-header-3'}).text
    total_vacancies = total_vacancies_text.split()[1].replace("\xa0", '')

    return total_vacancies, all_vacancies

def collect_resumes(query, filters):
    filter_string = ""
    if "высшее" in filters.values():
        filter_string += "&education_level=higher"
    for key in filters.values():
        filter_string += filter_map[key]

    main_url = f"https://hh.ru/search/resume?text={query}&ored_clusters=true&order_by=relevance&search_period=0&logic=normal&pos=full_text&exp_period=all_time&hhtmFrom=resume_search_result&hhtmFromLabel=resume_search_line" + filter_string
    response = requests.get(url=main_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    pager = soup.find_all(class_="pager-item-not-in-short-range")
    num_pages = int(pager[-1].text)

    urls = [f"https://hh.ru/search/resume?text={query}&ored_clusters=true&order_by=relevance&search_period=0&logic=normal&pos=full_text&exp_period=all_time&page={page}" + filter_string for page in range(1, num_pages)]
    with Pool(5) as p:
        resume_groups = p.map(fetch_resume_info, urls)

    all_resumes = [resume for group in resume_groups for resume in group]
    total_resumes_text = soup.find(attrs={'data-qa': 'bloko-header-3'}).text
    total_resumes = total_resumes_text.split()[1].replace("\xa0", '')

    return total_resumes, all_resumes
