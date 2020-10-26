# face-recognition
## Установка
Данный гайд по установке неокончательный и действителен для версии приложения на 26.10.2020.
### Обычная установка
Было обнаружено, что приложение не работает на python версии 3.7 и более новых. Оптимально использовать Python 3.6

1) Скачайте и разархивируйте репозиторий или склонируйте его
``` shell
git clone https://github.com/Girundi/face-recognition.git
```
2) Следуя гайдам, установите библиотеку dlib

* [Windows](https://coderoad.ru/41912372/%D1%83%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BA%D0%B0-dlib-%D0%BD%D0%B0-Windows-10)

* [Mac/Linux](https://www.pyimagesearch.com/2018/01/22/install-dlib-easy-complete-guide/)

3) Установите PyTorch с официального сайта. Для более стабильной работы рекомендуется установить версию с CUDA, даже если не предпологается использование GPU-ускорения

* [Ссылка на PyTorch](https://pytorch.org/get-started/locally/)

4) Установите остальные библиотеки
``` shell
pip install -r requirements.txt
```

5) Добавьте в головную директорию файлы для Google API

* [Файлы](https://drive.google.com/drive/folders/1H1_VsobQWyjgP9SHTdibDa3U6ZGzg2rV?usp=sharing)

6) Если это перенос на новое место, то создайте проект в Google Console следуя [гайду](https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html). Создайте веб-сервис и сервисный аккаунт и добавьте соответствующие JSON-файлы в головную директорию проекта.

7) Добавьте модель RetinaFace в директорию weights внутри проекта. Он тяжеловат для GitHub. 

* [Файл](https://drive.google.com/file/d/1RPpTYVMQb9H41u9JK_FXiuY15YJFCxSs/view?usp=sharing)

8) Установите [Redis](https://redis.io/download) и запустите его 

```
src/redis-server
```

9) Запустите Worker'а в головной директории проекта

```
celery -A app.celery worker --loglevel=info
```

10) Запустите из приложение
``` python
python app.py
```
