"""
Чтение данных из .csv файлов и их запись в БД.

Данные загружаются командой:
python manage.py load_data model_name path
model_name - имя модели, в которую передаются данные.
path - путь до файла *.csv
Так как модели связаны внешними ключами, то заполнять базу нужно в сл. порядке:

python manage.py load_data User static/data/users.csv
python manage.py load_data Category static/data/category.csv
python manage.py load_data Genre static/data/genre.csv
python manage.py load_data Title static/data/titles.csv
python manage.py load_data Review static/data/review.csv
python manage.py load_data Comment static/data/comments.csv
python manage.py load_data GenreTitle static/data/genre_title.csv
"""

import csv
import sys

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from django.db.models import Model
from reviews.models import (Category, Comment, Genre, GenreTitle, Review,
                            Title, User)


class Command(BaseCommand):
    help = ('Загрузка данных из CSV файлов и запись их в БД. '
            'Укажите имя модели и путь до файла CSV через пробел.')

    # Словарь для замены имен полей из csv файла на имена полей в модели.
    # А также для выбора объектов по внешнему ключу в цикле.
    MODELS_SWAP_FIELDS = {
        Title: {'category': (Category, 'category')},
        Review: {'title': (Title, 'title_id'), 'author': (User, 'author')},
        GenreTitle: {'title': (Title, 'title_id'),
                     'genre': (Genre, 'genre_id')},
        Comment: {'review': (Review, 'review_id'), 'author': (User, 'author')},
    }

    def add_arguments(self, parser) -> None:
        parser.add_argument('model', type=str,
                            help='Имя модели')
        parser.add_argument('file_path', type=str,
                            help='Путь до файла CSV')

    def handle(self, *args, **options) -> None:
        model_name: str = options['model']
        file_path: str = options['file_path']
        self.load_data(model_name, file_path)

    def load_data(self, model_name: str, file_path: str) -> None:
        """Записывает данные из csv файла в БД."""
        try:
            model: Model = apps.get_model(app_label='reviews',
                                          model_name=model_name)
        except LookupError:
            raise CommandError(f'Model {model_name} not found')

        objects_list: list = self.__create_objects_list_from_file(
            model, file_path)

        try:
            model.objects.bulk_create(objects_list)
        except IntegrityError as e:
            sys.stdout.write(
                self.style.WARNING(
                    f'При записи в БД возникли исключения,'
                    f' проверьте БД:{e}\n'))
        finally:
            sys.stdout.write(
                self.style.NOTICE(f'Данные из файла {file_path} обработаны.'))

    def __create_objects_list_from_file(self, model: Model,
                                        file_path: str) -> list:
        """Формирует список из объектов переданной
         модели с данными из файла csv."""
        objects_list = []
        with open(file_path, 'r', encoding='UTF-8') as f:
            reader: csv.DictReader = csv.DictReader(f)
            for row in reader:
                if model.objects.filter(id=row['id']).exists():
                    sys.stdout.write(
                        self.style.NOTICE(
                            f'Объект с id = {row["id"]} уже существует.\n'))
                    continue

                if model in self.MODELS_SWAP_FIELDS:
                    try:
                        for fld, val in self.MODELS_SWAP_FIELDS[model].items():
                            row[fld] = val[0].objects.get(id=row.pop(val[1]))
                    except ObjectDoesNotExist as e:
                        sys.stdout.write(
                            self.style.NOTICE(
                                f'{e}\nОбъект по внешнему ключу не найден.\n'
                                f'Проверьте связанные таблицы.\n'
                                f'Запись не добавлена: {row}\n'))
                        continue

                objects_list.append(model(**row))

        return objects_list
