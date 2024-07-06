import unittest
from app.Parser_hh_ru import get_vacancies, get_resumes

class TestParser(unittest.TestCase):

    def test_get_vacancies_no_filter(self):
        total, vacancies = get_vacancies("", {})
        self.assertGreater(total, 0)
        self.assertTrue(vacancies)

    def test_get_vacancies_filter_experience_education_schedule(self):
        filter_criteria = {
            'Опыт работы': 'от 1 года до 3 лет',
            'Образование': 'среднее профессиональное',
            'График работы': 'полный день'
        }
        total, vacancies = get_vacancies("", filter_criteria)
        self.assertGreater(total, 0)
        self.assertTrue(vacancies)

    def test_get_vacancies_filter_no_experience_remote(self):
        filter_criteria = {
            'Опыт работы': 'нет опыта',
            'Образование': 'не требуется или не указано',
            'График работы': 'удаленная работа'
        }
        total, vacancies = get_vacancies("", filter_criteria)
        self.assertGreater(total, 0)
        self.assertTrue(vacancies)

    def test_get_resumes_no_filter(self):
        total, resumes = get_resumes("", {})
        self.assertGreater(total, 0)
        self.assertTrue(resumes)

    def test_get_resumes_filter_no_experience_special_education_shift_work(self):
        filter_criteria = {
            'Опыт работы': 'нет опыта',
            'Образование': 'среднее специальное',
            'График работы': 'вахтовый метод'
        }
        total, resumes = get_resumes("", filter_criteria)
        self.assertGreater(total, 0)
        self.assertTrue(resumes)

    def test_get_resumes_filter_no_experience_any_education_any_schedule(self):
        filter_criteria = {
            'Опыт работы': 'нет опыта',
            'Образование': 'не имеет значения',
            'График работы': 'не имеет значения'
        }
        total, resumes = get_resumes("", filter_criteria)
        self.assertGreater(total, 0)
        self.assertTrue(resumes)

if __name__ == '__main__':
    unittest.main()
