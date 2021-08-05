
from io import TextIOWrapper
import os
from dotenv import load_dotenv, dotenv_values
import re
from typing import List, Union
from colorama import Fore, init
from datetime import datetime
from random import randint
from ibm_watson import LanguageTranslatorV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

load_dotenv()
init(autoreset=True)

config = dotenv_values(".env")

pathModule = config['PATH_MODULE']
moduleName = config['MODULE_NAME']

language_translator = None
if config['TRANSLATE_TO_ENG'] == 'Y' and config['IBM_API_KEY'] != '' and config['IBM_URL'] != '':
    authenticator = IAMAuthenticator(config['IBM_API_KEY'])
    language_translator = LanguageTranslatorV3(
        version='2018-05-01',
        authenticator=authenticator
    )
    language_translator.set_service_url(config['IBM_URL'])


class EmptyValue(Exception):
    """Исключение если значение пустое"""
    pass


class EmptyValueKey(Exception):
    """Исключение если ключ пуст"""

    def __init__(self, tKey):
        self.tKey = tKey


class DifferentVariables(Exception):
    """Исключение если переменные разные"""
    pass


class DifferentCountVariables(Exception):
    """Исключение если разное количество переменных"""
    pass


class ForbiddenRewriting(Exception):
    """Исключение если будет перезапись ключа"""

    def __init__(self, key, tKey):
        self.key = key
        self.tKey = tKey


class NoSelect(Exception):
    """Исключение если не выбрана никакая опция"""
    pass


resources = {}
resourcesFileName = 'resources_'+str(randint(1, 999999))+'.txt'


def checkTKey(textKey: str):
    """Проверка ключа в resources

    Args:
        textKey (str): ключ
    """
    def checkStructure(structure: str, listKey: List[str]):
        """Рекурсивная проверка дерева 

        Args:
            structure (str): текущая структура проверки
            listKey (List[str]): оставшиеся ключи

        Raises:
            EmptyValueKey: вызываем если ключ пуст
            ForbiddenRewriting: вызываем если будет перезапись
        """
        key = listKey.pop(0)
        if key == '':
            raise EmptyValueKey(textKey)
        if (len(listKey) == 0):
            if key in structure:
                raise ForbiddenRewriting(key, textKey)
        else:
            if key in structure and type(structure[key]) == str:
                raise ForbiddenRewriting(key, textKey)
            else:
                structure[key] = structure[key] if key in structure else {}
                checkStructure(structure[key], listKey)
    resources['EN'] = resources['EN'] if 'EN' in resources else {}
    checkStructure(resources['EN'], textKey.split('.'))


def addResources(text: str, textKey: str, lang: str) -> None:
    """Добавление ключа с текстом English / Russian версий, в дерево resources

    Args:
        text (str): текст
        textKey (str): ключ
        lang (str): EN / RU версия
    """
    def setStructure(structure: str, listKey: List[str]):
        key = listKey.pop(0)
        if (len(listKey) == 0):
            structure[key] = text
        else:
            structure[key] = structure[key] if key in structure else {}
            setStructure(structure[key], listKey)
    resources[lang] = resources[lang] if lang in resources else {}
    setStructure(resources[lang], textKey.split('.'))


def saveResources() -> None:
    """Генерирует текст в виде типа данных Object в JavaScript
    и сохраняет этот текст в файл

    Returns:
        None: None
    """
    space = ''

    def getText(resources: dict, space: str):
        text = ''
        for key in resources:
            if (type(resources[key]) == str):
                text = text+space+key+': \''+resources[key]+'\',\n'
            else:
                text = text+space+key + \
                    ': {\n'+getText(resources[key],
                                    space+'   ')+space+'},\n'
        return text
    text = getText(resources, space)
    mode = 'w' if os.path.isfile(resourcesFileName) else 'a'
    with open(resourcesFileName, mode, encoding='utf-8') as f:
        f.write(text)
        f.close()


def getVarText(varList: Union[List[dict], List]) -> str:
    """Получения переменных со значением в виде текста через запятую

    Args:
        varList (Union[List[dict], List]): список словарей [{ varName, value }, ...]

    Returns:
        str: переменные со значениями в виде текста через запятую
    """
    varText = ''
    if (varList != None and len(varList)):
        varTextList = []
        for var in varList:
            varTextList.append(var['varName']+': '+var['value']
                               if var['varName'] != var['value'] else var['varName'])
        varText = ', '.join(varTextList)
    return varText


def checkVar(t: str, inputEnable: bool = True) -> Union[List[dict], List]:
    """Получение переменных (inputEnable=True) или проверка переменных (inputEnable=False)

    Args:
        t (str): текст строки English или Russian версии
        inputEnable (bool, optional): если необходим вывод с получением переменных и их значений иначе просто проверка переменных. Defaults to True.

    Raises:
        EmptyValue: если указаное значение пусто

    Returns:
        Union[List[dict], List]: возвращаем переменные в виде списка словорей [{ varName, value }, ...]
    """
    if(re.search('\{\{[a-z]+\}\}', t, flags=re.IGNORECASE)):
        try:
            if inputEnable:
                print('', end='\n')
                print(Fore.MAGENTA+'В переводе обнаружены переменные', end='\n')
            varList = []
            for var in re.findall('\{\{([a-z]+)\}\}', t, flags=re.IGNORECASE):
                value = input(
                    'Укажите значение для переменной "{{'+var+'}}": ') if inputEnable else ''
                if inputEnable and value == '':
                    raise EmptyValue
                varList.append({
                    'varName': var,
                    'value': value,
                })
        except EmptyValue:
            print(
                Fore.RED+'Ошибка! Значение переменной не может быть пустым, укажите переменные снова', end='\n')
            checkVar(t, inputEnable)
        else:
            if inputEnable:
                print('', end='\n')
                print(Fore.MAGENTA +
                      'Для переменных указаны следующие значения:', end='\n')
                for var in varList:
                    print('{{'+var['varName']+'}} -> '+var['value'], end='\n')
                print('', end='\n')
            save = input(
                'Сохранить переменные? (y/n): ') if inputEnable else 'Y'
            if (save == 'Y' or save == 'y'):
                return varList
            else:
                repeat = input('Повторить определение переменных? (y/n): ')
                if (repeat == 'Y' or repeat == 'y'):
                    return checkVar(t, inputEnable)
                else:
                    return []
    return []


def translite(file: os.DirEntry, lines: List[str], numLine: int, textExclusion: str, textReplace: str) -> None:
    """Указываем English / Russina версии переводов и всякие проверки

    Args:
        file (os.DirEntry): файл, который парсим (его будем изменять)
        lines (List[str]): все строки в файле
        numLine (int): номер строки в файле, который парсим
        textExclusion (str): текст в строке который был ранее распарсен
        textReplace (str): регулярное выражение для замены

    Raises:
        EmptyValue: вызываем если было указано пустое значение
        DifferentCountVariables: вызываем если количество переменных отличается
        DifferentVariables: вызываем если переменные отличается
    """
    try:
        translation = 'Нет перевода...'
        if language_translator != None:
            translation = language_translator.translate(
                text=textExclusion, model_id='ru-en').get_result()
            translation = translation['translations'][0]['translation']
        print('', end='\n')
        print('Предлагаем English вариант для "' +
              textExclusion+'": '+translation, end='\n')
        tEn = input('Напишите English вариант для "'+textExclusion+'": ')
        if tEn == '':
            raise EmptyValue
        tRu = input('Напишите Russian вариант для "'+textExclusion+'": ')
        if tRu == '':
            raise EmptyValue
        if len(checkVar(tEn, False)) != len(checkVar(tRu, False)):
            raise DifferentCountVariables
        if getVarText(checkVar(tEn, False)) != getVarText(checkVar(tRu, False)):
            raise DifferentVariables
        varText = getVarText(checkVar(tEn))
        print('', end='\n')
        print(Fore.MAGENTA +
              'Для построения дерева ключей можно использовать символ "."\n----------\nНапример при вводе: example.getData - итоговое выражение для перевода будет таким: t(\''+moduleName+'.example.getData\', { ... })\nИмя модуля ('+moduleName+') добавляется автоматически.\nA файл с переводом будет добавлено:\n\nerror: {\n   getData: \''+tRu+'\',\n},\n----------', end='\n\n')
        # print('Предлагаем следующий ключ: ....................', end='\n')
        tKey = input('Напишите ключ для перевода: ')
        if tKey == '':
            raise EmptyValue
        checkTKey(tKey)
        replaceTextY = '{t(\''+moduleName+'.'+tKey+'\'' + \
            ('' if varText == '' else ', { '+varText+' }')+')}'
        replaceTextN = 't(\''+moduleName+'.'+tKey+'\'' + \
            ('' if varText == '' else ', { '+varText+' }')+')'
        print('', end='\n')
        print('Добавить фигурные скобки?', end='\n')
        print('', end='\n')
        print('Если да (y):', end='\n')
        print(str(numLine+1)+': ' +
              lines[numLine].replace(textReplace, replaceTextY, 1))
        print('', end='\n')
        print('Если нет (n):', end='\n')
        print(str(numLine+1)+': ' +
              lines[numLine].replace(textReplace, replaceTextN, 1))
        print('', end='\n')
        addCurlyBraces = input('(y/n): ')
        if (addCurlyBraces == 'Y' or addCurlyBraces == 'y'):
            replaceText = replaceTextY
        else:
            replaceText = replaceTextN
        replaceLine = lines[numLine].replace(textReplace, replaceText, 1)
        print('', end='\n')
        print(Fore.MAGENTA+'Новая строка:')
        print(str(numLine+1)+': '+replaceLine, end='\n\n')
        save = input('Сохраняем? (y/n): ')
        if (save == 'Y' or save == 'y'):
            addResources(tEn, tKey, 'EN')
            addResources(tRu, tKey, 'RU')
            with open(file, 'w', encoding='utf-8') as f:
                lines[numLine] = replaceLine
                f.writelines(lines)
                f.close()
                saveResources()
                timestr = datetime.now().strftime('%H:%M:%S')
                print(Fore.GREEN+timestr+' Сохранено!', end='\n\n')
        else:
            repeat = input('Повторить перевод? (y/n): ')
            if (repeat == 'Y' or repeat == 'y'):
                translite(file, lines, numLine, textExclusion, textReplace)
            else:
                repeat = input(
                    'Перейти снова к выбору действий для данной строки? (y/n): ')
                if (repeat == 'Y' or repeat == 'y'):
                    selectAction(file, lines, numLine,
                                 textExclusion, textReplace)
                else:
                    print('', end='\n\n')
    except DifferentCountVariables:
        print(Fore.RED+'Ошибка! Разное количество переменных в English / Russian версиях, повторите перевод', end='\n')
        translite(file, lines, numLine, textExclusion, textReplace)
    except DifferentVariables:
        print(Fore.RED+'Ошибка! Разные переменные в English / Russian версиях, повторите перевод', end='\n')
        translite(file, lines, numLine, textExclusion, textReplace)
    except EmptyValue:
        print(Fore.RED+'Ошибка! Значение не может быть пустым, повторите перевод', end='\n')
        translite(file, lines, numLine, textExclusion, textReplace)
    except EmptyValueKey as e:
        print(Fore.RED+'Один из ключей: '+e.tKey +
              ' - пуст. Ключ не может быть пустым! Повторите перевод', end='\n')
        translite(file, lines, numLine, textExclusion, textReplace)
    except ForbiddenRewriting as e:
        print(Fore.RED+'Ошибка! В указанный ключ: '+e.key +
              ' ('+e.tKey+') уже что-то было записано.', end='\n')
        print(Fore.RED+'Повторите перевод, укажите другой ключ...', end='\n')
        translite(file, lines, numLine, textExclusion, textReplace)
    except Exception:
        print(Fore.RED+'Хм, какая-то не предвиденная ошибка =/ ... попробуйте перевести повторно', end='\n')
        translite(file, lines, numLine, textExclusion, textReplace)


def markNoTranslite(file: os.DirEntry, lines: List[str], numLine: int, textExclusion: str, textReplace: str) -> None:
    """Отмечаем строку как не переведенной

    Args:
        file (os.DirEntry): файл, который парсим (его будем изменять)
        lines (List[str]): все строки в файле
        numLine (int): номер строки в файле, который парсим
        textExclusion (str): текст в строке который был ранее распарсен
        textReplace (str): регулярное выражение для замены
    """
    replaceLine = re.sub(
        r'(.*)\n$', r'\1 // НЕ ПЕРЕВЕДЕННО !!!\n', lines[numLine], flags=re.IGNORECASE)
    print('', end='\n')
    print(Fore.MAGENTA+'Новая строка:')
    print(str(numLine+1)+': '+replaceLine, end='\n\n')
    save = input('Сохраняем? (y/n): ')
    if (save == 'Y' or save == 'y'):
        with open(file, 'w', encoding='utf-8') as f:
            lines[numLine] = replaceLine
            f.writelines(lines)
            f.close()
            timestr = datetime.now().strftime('%H:%M:%S')
            print(Fore.GREEN+timestr+' Сохранено!', end='\n\n')
    else:
        repeat = input(
            'Перейти снова к выбору действий для данной строки? (y/n): ')
        if (repeat == 'Y' or repeat == 'y'):
            selectAction(file, lines, numLine,
                         textExclusion, textReplace)
        else:
            print('', end='\n\n')


def selectKeyTranslite(file: os.DirEntry, lines: List[str], numLine: int, textExclusion: str, textReplace: str) -> None:
    """Указываем существующий перивод

    Args:
        file (os.DirEntry): файл, который парсим (его будем изменять)
        lines (List[str]): все строки в файле
        numLine (int): номер строки в файле, который парсим
        textExclusion (str): текст в строке который был ранее распарсен
        textReplace (str): регулярное выражение для замены
    """
    print('', end='\n')
    print('Чем заменить строку "'+textExclusion+'"? ')
    print('Выберите опцию:')
    print('1 - использовать существующий ключ;')
    print('2 - использовать выражение типа: t(\'' +
          moduleName+'.ключ\', { ... }):;')
    print('3 - вернутся назад;')
    select = input(': ')
    try:
        replaceText = None
        if select == '1':
            replaceText = input('Укажите ключ: ')
            replaceText = 't(\''+replaceText+'\')'
        elif select == '2':
            replaceText = input(
                'Укажите ключ, типа: t(\''+moduleName+'.ключ\', { ... }): ')
        elif select == '3':
            selectAction(file, lines, numLine,
                         textExclusion, textReplace)
        else:
            raise NoSelect
        if replaceText != None:
            replaceTextY = '{'+replaceText+'}'
            replaceTextN = replaceText
            print('', end='\n')
            print('Добавить фигурные скобки?', end='\n')
            print('', end='\n')
            print('Если да (y):', end='\n')
            print(str(numLine+1)+': ' +
                lines[numLine].replace(textReplace, replaceTextY, 1))
            print('', end='\n')
            print('Если нет (n):', end='\n')
            print(str(numLine+1)+': ' +
                lines[numLine].replace(textReplace, replaceTextN, 1))
            print('', end='\n')
            addCurlyBraces = input('(y/n): ')
            if (addCurlyBraces == 'Y' or addCurlyBraces == 'y'):
                replaceText = replaceTextY
            else:
                replaceText = replaceTextN
            replaceLine = lines[numLine].replace(textReplace, replaceText, 1)
            print('', end='\n')
            print(Fore.MAGENTA+'Новая строка:')
            print(str(numLine+1)+': '+replaceLine, end='\n\n')
            save = input('Сохраняем? (y/n): ')
            if (save == 'Y' or save == 'y'):
                with open(file, 'w', encoding='utf-8') as f:
                    lines[numLine] = replaceLine
                    f.writelines(lines)
                    f.close()
                    timestr = datetime.now().strftime('%H:%M:%S')
                    print(Fore.GREEN+timestr+' Сохранено!', end='\n\n')
            else:
                repeat = input(
                    'Перейти снова к выбору действий для данной строки? (y/n): ')
                if (repeat == 'Y' or repeat == 'y'):
                    selectAction(file, lines, numLine,
                                 textExclusion, textReplace)
                else:
                    print('', end='\n\n')
    except NoSelect:
        selectKeyTranslite(file, lines, numLine, textExclusion, textReplace)


def selectAction(file: os.DirEntry, lines: List[str], numLine: int, textExclusion: str, textReplace: str) -> None:
    """Выбор действия по найденой строке

    Args:
        file (os.DirEntry): файл, который парсим (его будем изменять)
        lines (List[str]): все строки в файле
        numLine (int): номер строки в файле, который парсим
        textExclusion (str): текст в строке который был ранее распарсен
        textReplace (str): регулярное выражение для замены
    """
    print('Выберите опцию:')
    print('1 - игнорировать;')
    print('2 - перевести;')
    print('3 - отметить как непереведенное;', end='\n')
    print('4 - использовать существующий перевод;', end='\n')
    select = input(': ')
    if select == '1':
        print(Fore.MAGENTA+' ... игнорировано', end='\n')
    elif select == '2':
        print(Fore.MAGENTA+' ... переводим:', end='\n')
        print(Fore.MAGENTA +
              'В переводе можно указать переменные, например: {{yourVarName}}', end='\n')
        translite(file, lines, numLine, textExclusion, textReplace)
    elif select == '3':
        print(Fore.MAGENTA+' ... отмечено как не переведенно', end='\n')
        markNoTranslite(file, lines, numLine, textExclusion, textReplace)
    elif select == '4':
        print(Fore.MAGENTA+' ... используем существующий перевод', end='\n')
        selectKeyTranslite(file, lines, numLine, textExclusion, textReplace)
    else:
        selectAction(file, lines, numLine, textExclusion, textReplace)


def parseFile(file: os.DirEntry) -> None:
    """Парсер файла

    Args:
        file (os.DirEntry): файл
    """
    timestr = datetime.now().strftime('%H:%M:%S')
    print(Fore.YELLOW+timestr+': Начинаем читать файл: '+file.name)
    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        f.close()
        numLine = -1
        for line in lines:
            numLine += 1
            # если комментарий выходим...
            if (re.search('^[\s\t]*\/\/', line, flags=re.IGNORECASE)):
                continue
            # если комментарий выходим...
            if (re.search('^[\s\t]*\/\*', line, flags=re.IGNORECASE)):
                continue
            # если комментарий выходим...
            if (re.search('^[\s\t]*\*', line, flags=re.IGNORECASE)):
                continue
            # если комментарий, который сделан в процессе работы этого скрипта - выходим...
            if (re.search('//\sНЕ\sПЕРЕВЕДЕННО\s!!!', line, flags=re.IGNORECASE)):
                continue

            if (re.search('[а-я]+', line, flags=re.IGNORECASE)):  # если кириллица
                listRegex = [
                    {
                        'searchRegexInclusion': '(`[^`]*[а-я]+[^`]*`)',
                        'searchRegexExclusion': r'(?:`)+([^`]*[а-я]+[^`]*)(?:`)+',
                        'comment': 'Обнаружено полное соответствие шаблону (`) в строке ('+str(numLine+1)+'):',
                        'inclusion': True,
                    },
                    {
                        'searchRegexInclusion': '(\'[^\']*[а-я]+[^\']*\')',
                        'searchRegexExclusion': r'(?:\')+([^\']*[а-я]+[^\']*)(?:\')+',
                        'comment': 'Обнаружено полное соответствие шаблону (\') в строке ('+str(numLine+1)+'):',
                        'inclusion': True,
                    },
                    {
                        'searchRegexInclusion': '("[^"]*[а-я]+[^"]*")',
                        'searchRegexExclusion': r'(?:")+([^"]*[а-я]+[^"]*)(?:")+',
                        'comment': 'Обнаружено полное соответствие шаблону (") в строке ('+str(numLine+1)+'):',
                        'inclusion': True,
                    },
                    {
                        'searchRegexInclusion': '(>[^>]*[а-я]+[^<]*<)',
                        'searchRegexExclusion': r'(?:>)+([^>]*[а-я]+[^<]*)(?:<)+',
                        'comment': 'Обнаружено полное соответствие шаблону (><) в строке ('+str(numLine+1)+'):',
                        'inclusion': False,
                    },
                ]
                textInclusion = None
                for regex in listRegex:
                    if (re.search(regex['searchRegexInclusion'], line, flags=re.IGNORECASE)):
                        print(
                            '-----------------------------------------------------------', end='\n')
                        print(Fore.MAGENTA+timestr+': '+regex['comment'])
                        if (numLine-3) >= 0: print(str(numLine-2)+': '+lines[numLine-3], end='')
                        if (numLine-2) >= 0: print(str(numLine-1)+': '+lines[numLine-2], end='')
                        if (numLine-1) >= 0: print(str(numLine-0)+': '+lines[numLine-1], end='')
                        print(Fore.GREEN+str(numLine+1)+': '+line, end='') # <<< найденная строка тут
                        if (numLine+1) <= len(lines): print(str(numLine+2)+': '+lines[numLine+1], end='')
                        if (numLine+2) <= len(lines): print(str(numLine+3)+': '+lines[numLine+2], end='')
                        if (numLine+3) <= len(lines): print(str(numLine+4)+': '+lines[numLine+3], end='')
                        for textInclusion in re.findall(regex['searchRegexInclusion'], line, flags=re.IGNORECASE):
                            textExclusion = re.sub(
                                regex['searchRegexExclusion'], r'\1', textInclusion, flags=re.IGNORECASE)
                            print('', end='\n')
                            print(Fore.MAGENTA+'Найдено:')
                            print(textExclusion, end='\n\n')
                            textReplace = textInclusion if regex['inclusion'] == True else textExclusion
                            selectAction(file, lines, numLine,
                                         textExclusion, textReplace)

                # если комментарий (после попытки обнаружения кириллицы по шаблонам в этой же строке) выходим...
                if (re.search('(?:\/\/)+.*[а-я]+.*', line, flags=re.IGNORECASE)):
                    continue
                # если комментарий (после попытки обнаружения кириллицы по шаблонам в этой же строке) выходим...
                elif (re.search('(?:\/\*)+.*[а-я]+.*', line, flags=re.IGNORECASE)):
                    continue
                else:
                    if (textInclusion == None):
                        print(
                            Fore.RED+timestr+': Обнаружена кирилица без шаблона в строке ('+str(numLine)+'):', end='\n')
                        print(line)
        print('-----------------------------------------------------------', end='\n')


def scandir(pathModule: str) -> None:
    """Сканирование каталога

    Args:
        pathModule (str): путь до каталога
    """
    timestr = datetime.now().strftime('%H:%M:%S')
    print(Fore.GREEN+timestr+': Начинаем сканировать каталог: '+pathModule)
    for file in os.scandir(pathModule):
        if file.is_dir():
            print(Fore.GREEN+timestr+': Обнаружен каталог: '+file.path)
            scandir(file.path)
        else:
            if re.search('\.(:?js|ts|jsx|tsx)$', file.name, flags=re.IGNORECASE):
                print(Fore.CYAN+timestr+': Обнаружен файл: '+file.name)
                parseFile(file)


scandir(pathModule)
