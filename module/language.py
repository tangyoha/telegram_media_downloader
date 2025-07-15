"""Multi language support"""

# disable pylint: disable = C0301
from enum import Enum


class Language(Enum):
    """Language for ui"""

    EN = 1  # english
    ZH = 2  # china
    RU = 3  # russian
    UA = 4  # ukrainian


_language = Language.EN


def set_language(language: Language):
    """Set Lanaguage"""
    # pylint: disable = W0603
    global _language
    _language = language


translations = {
    "Forward": ["转发", "Переслать", "Переслати"],
    "Total": ["总数", "Всего", "Всього"],
    "Success": ["成功", "Успешно", "Успішно"],
    "Failed": ["失败", "Не удалось", "Не вдалося"],
    "Skipped": ["跳过", "Пропущено", "Пропущено"],
    "Message ID": ["消息ID", "ID сообщения", "ID повідомлення"],
    "Telegram Media Downloader": [
        "电报媒体下载器",
        "Telegram Media Downloader",
        "Telegram Media Downloader",
    ],
    "Version": ["版本", "Версия", "Версія"],
    "Downloading": ["下载", "Скачивание", "Скачування"],
    "Available commands:": ["可用命令:", "Доступные команды:", "Доступні команди:"],
    "Show available commands": [
        "显示可用命令",
        "Показать доступные команды",
        "Показати доступні команди",
    ],
    "Download messages": ["下载消息", "Скачать сообщения", "Скачати повідомлення"],
    "Forward messages": ["转发消息", "Переслать сообщения", "Переслати повідомлення"],
    "Listen for forwarded messages": [
        "监听转发消息",
        "Прослушивать пересланные сообщения",
        "Прослуховувати переслані повідомлення",
    ],
    "Set language": ["设置语言", "Установить язык", "Встановити мову"],
    "**Note**: 1 means the start of the entire chat": [
        "**注意**: 1表示整个聊天的开始",
        "**Примечание**: 1 означает начало всего чата",
        "**Увага**: 1 означає початок всього чату",
    ],
    "0 means the end of the entire chat": [
        "0表示整个聊天的结束",
        "0 означает конец всего чата",
        "0 означає кінець всього чату",
    ],
    "means optional, not required": [
        "表示可选项，非必填",
        "означает необязательный параметр",
        "означає необов'язковий параметр",
    ],
    "To download the video, use the method to directly enter /download to view": [
        "下载视频，使用方法直接输入/download查看",
        "Чтобы скачать видео, введите /download для просмотра",
        "Щоб скачати відео, введіть /download для перегляду",
    ],
    "Forward video, use the method to directly enter /forward to view": [
        "转发视频，使用方法直接输入/forward查看",
        "Переслать видео, введите /forward для просмотра",
        "Переслати відео, введіть /forward для перегляду",
    ],
    "Listen forward, use the method to directly enter /listen_forward to view": [
        "监控转发，使用方法直接输入/listen_forward查看",
        "Слушать пересылку, введите /listen_forward для просмотра",
        "Слухати пересилання, введіть /listen_forward для перегляду",
    ],
    "Add download filter, use the method to directly enter /add_filter to view": [
        "添加下载过滤器",
        "Добавить фильтр загрузки, используйте метод, чтобы непосредственно ввести /add_filter для просмотра",
        "Додати фільтр завантаження, використовуйте метод, щоб безпосередньо ввести /add_filter для перегляду",
    ],
    "Help": ["帮助", "Помощь", "Допомога"],
    "Invalid command format": [
        "无效的命令格式",
        "Неверный формат команды",
        "Невірний формат команди",
    ],
    "Invalid command format. Please use /set_language en/ru/zh/ua": [
        "无效的命令格式。请使用 /set_language en/ru/zh/ua",
        "Неверный формат команды. Пожалуйста, используйте /set_language en/ru/zh/ua",
        "Невірний формат команди. Будь ласка, використовуйте /set_language en/ru/zh/ua",
    ],
    "Language set to English": [
        "语言设置为中文",
        "Выбран английский язык",
        "Обрано англійську мову",
    ],
    "Language set to": [
        "语言设置为",
        "Выбран язык",
        "Обрано мову",
    ],
    "Invalid command format. Please use /add_filter your filter": [
        "无效的命令格式。请使用 /add_filter 你的过滤规则",
        "Неверный формат команды. Пожалуйста, используйте /add_filter ВашФильтр",
        "Невірний формат команди. Будь ласка, використовуйте /add_filter ВашФільтр",
    ],
    "Add download filter": [
        "添加下载过滤器",
        "Добавить фильтр скачивания",
        "Додати фільтр скачування",
    ],
    "Check error, please add again": [
        "检验错误,请重新添加",
        "Ошибка проверки, пожалуйста, добавьте еще раз",
        "Помилка перевірки, будь ласка, додайте ще раз",
    ],
    "Direct download, directly forward the message to your robot": [
        "直接下载，直接转发消息给你的机器人",
        "Скачивание напрямую, пересылка сообщения напрямую вашему роботу",
        "Безпосереднє скачування, безспесередня пересилка повідомлення вашому роботу",
    ],
    "Directly download a single message": [
        "直接下载单条消息",
        "Прямое скачивание одного сообщения",
        "Безпосереднє скачування одного повідомлення",
    ],
    "From": ["从", "От", "Від"],
    "download": ["下载", "скачать", "скачати"],
    "error": ["错误", "ошибка", "помилка"],
    "Parameter error, please enter according to the reference format": [
        "参数错误,请根据参考格式输入",
        "Ошибка параметра, введите в соответствии с форматом ссылки",
        "Помилка параметра, введіть відповідно до формату посилання",
    ],
    "Download all messages of common group": [
        "下载公共群组的所有消息",
        "Скачать все сообщения общей группы",
        "Скачати всі повідомлення спільної групи",
    ],
    "The private group (channel) link is a random group message link": [
        "私密群组(频道) 链接为随便复制一条群组消息链接",
        "Ссылка на частную группу (канал) - это ссылка на случайное сообщение группы",
        "Посилання на приватну групу (канал) - це посилання на випадкове повідомлення групи",
    ],
    "The download starts from the N message to the end of the M message": [
        "下载从第N条消息开始的到第M条信息结束",
        "Скачивание начинается с сообщения N до конца сообщения M",
        "Скачування починається з повідомлення N до кінця повідомлення M",
    ],
    "When M is 0, it means the last message. The filter is optional": [
        "M为0的时候表示到最后一条信息,过滤器为可选",
        "Когда M равно 0, это означает последнее сообщение. Фильтр необязателен",
        "Коли M дорівнює 0, це означає останнє повідомлення. Фільтр необов'язковий",
    ],
    "chat input error, please enter the channel or group link": [
        "chat输入错误，请输入频道或群组的链接",
        "Ошибка ввода чата, введите ссылку на канал или группу",
        "Помилка введеня чату, введіть посилання на канал або групу",
    ],
    "Error type": ["错误类型", "Тип ошибки", "Тип помилки"],
    "Exception message": ["异常消息", "Сообщение исключения", "Повідомлення винятка"],
    "Invalid chat link": [
        "无效的聊天链接",
        "Ошибочная ссылка на чат",
        "Помилкове посилання на чат",
    ],
    "Cannot be forwarded to this bot, will cause an infinite loop": [
        "不能转发给该机器人，会导致无限循环",
        "Невозможно переслать этому боту, это вызовет бесконечный цикл",
        "Неможливо переслати цьому боту, це спричинить безкінечний цикл",
    ],
    "Please use": ["请使用", "Пожалуйста, используйте", "Будь ласка, використовуйте"],
    "Filter": ["过滤器", "Фильтр", "Фільтр"],
    "Error forwarding message": [
        "失败的转发消息",
        "Ошибка пересылки сообщения",
        "Помилка пересилки повідомлення",
    ],
    "file reference expired, refetching": [
        "文件引用过期,重新获取中",
        "Ссылка на файл истекла, повторное получение",
        "Посилання на файл минуло, повторне отримання",
    ],
    "file reference expired for 3 retries, download skipped": [
        "文件引用过期重试超过3次,跳过下载",
        "Ссылка на файл истекла после 3 попыток, загрузка пропущена",
        "Посилання на файл минуло після 3 спроб, завантаження пропущено",
    ],
    "Timeout Error occurred when downloading Message": [
        "下载消息超时错误",
        "Ошибка времени ожидания при скачивании сообщения",
        "Помилка часу очікування при скачуванні повідомлення",
    ],
    "retrying": ["重试", "повторная попытка", "повторна спроба"],
    "seconds": ["秒", "секунд", "секунд"],
    "Timing out after 3 reties, download skipped": [
        "超时重试超过3次,跳过下载",
        "Истекло время ожидания после 3 попыток, загрузка пропущена",
        "Час очікування закінчився після 3 спроб, завантаження пропущено",
    ],
    "could not be downloaded due to following exception": [
        "无法下载,因为以下异常",
        "не может быть скачен по следующей причине",
        "не може бути скачаний з наступної причини",
    ],
    "Downloading files failed during last run": [
        "下载最后一次运行失败的文件",
        "Скачивание файлов не удалось во время последнего запуска",
        "Скачування файлів не вдалося під час останнього запуску",
    ],
    "Successfully started (Press Ctrl+C to stop)": [
        "成功启动(按Ctrl+C停止)",
        "Запуск успешный (нажмите Ctrl + C для остановки)",
        "Запуск успішний (натисніть Ctrl + C для зупинки)",
    ],
    "KeyboardInterrupt": ["键盘中断", "KeyboardInterrupt", "KeyboardInterrupt"],
    "update config": ["更新配置", "обновить конфигурацию", "оновити конфігурацію"],
    "Updated last read message_id to config file": [
        "更新最后阅读消息ID到配置文件",
        "Обновлен идентификатор последнего прочитанного сообщения в конфигурационном файле",
        "Оновлено ідентифікатор останнього прочитаного повідомлення у конфігураційному файлі",
    ],
    "total download": ["总下载", "всего скачено", "всього скачано"],
    "total upload file": ["总上传文件", "всего скаченных файлов", "всього скачаних файлів"],
    "Stopped": ["停止", "остановлено", "зупинено"],
    "already download,download skipped": [
        "已下载,已跳过下载",
        "уже скачен, скачивание пропущена",
        "вже скачан, скачування пропущено",
    ],
    "Media downloaded with wrong size": [
        "媒体下载错误的大小",
        "Медиафайл скачен с неправильным размером",
        "Медіафайл скачано з неправильним розміром",
    ],
    "actual": ["实际", "фактический", "фактичний"],
    "file name": ["文件名", "имя файла", "ім'я файлу"],
    "Successfully downloaded": ["成功下载", "Успешно скачано", "Успішно скачано"],
    "Get group and user info from message link": [
        "从消息链接中获取群组和用户信息",
        "Получить информацию о группе и пользователе по ссылке на сообщение",
        "Отримайте інформацію про групу та користувача за посиланням у повідомленні",
    ],
    "Upload Progresses": ["上传进度", "Прогресс загрузки", "Прогрес завантаження"],
    "Download Progresses": ["下载进度", "Прогресс скачивания", "Прогрес завантаження"],
    "New Version": ["新版本", "новая версия", "нова версія"],
    "Stop bot download or forward": [
        "停止机器人下载或转发",
        "Остановить загрузку или пересылку ботом",
        "Зупинити завантаження або пересилання ботом",
    ],
    "Forward a specific media to a comment section": [
        "将特定媒体转发至评论",
        "Переслать определенное медиа в комментарии",
        "Переслати конкретне медіа в коментарі",
    ],
    "Add replace advertisement filter": [
        "添加删除广告过滤器",
        "Добавить фильтр рекламы",
        "Додати фільтр реклами",
    ],
    "Remove replace advertisement filter": [
        "移除删除广告过滤器",
        "Удалить фильтр рекламы",
        "Видалити фільтр реклами",
    ],
    "Add filter advertisement filter": [
        "添加过滤广告过滤器",
        "Добавить фильтр рекламы",
        "Додати фільтр реклами",
    ],
    "Remove filter advertisement filter": [
        "移除过滤广告过滤器",
        "Удалить фильтр рекламы",
        "Видалити фільтр реклами",
    ],
    "Set add advertisement": [
        "设置添加广告",
        "Установить рекламу",
        "Встановити рекламу",
    ],
}


def _t(text: str):
    """Get translation
    Parameters
    ----------
    text : str
    language : str
    Returns
    -------
    str
    """
    if _language is Language.EN:
        return text

    if text in translations:
        return translations[text][_language.value - 2]

    return text
