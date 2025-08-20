# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-7k1!_mroo-p!$0&fqe7234i%v)7!9ikrq@r37door#qc9a3j#v'

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR = Path(__file__).resolve().parent.parent

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# MYSQL

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'test',
        'USER': 'root',
        'PASSWORD': '1234',
        'host' : 'localhost',
        'port' : '3306'
    }
}