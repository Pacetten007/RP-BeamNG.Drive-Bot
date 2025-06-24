import disnake
import os
from disnake.ext import tasks, commands
from disnake import ApplicationCommandInteraction
import random
import string
import sqlite3
from datetime import datetime, timedelta
import asyncio
import logging
from unbelievaboat import client
import io
from dotenv import load_dotenv
import json
from api import download_file_from_server, parse_player_data, add_player_to_whitelist, add_car_to_player, remove_car_from_player

discord_token = ""
unbelievatoken = ""

intents = disnake.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
unbclient = client(unbelievatoken)

conn = sqlite3.connect('everything.db')
cursor = conn.cursor()

# Создание таблиц для хранения данных
cursor.execute('''CREATE TABLE IF NOT EXISTS licenses (user_id TEXT,category TEXT,issue_date TEXT,status TEXT DEFAULT "active",PRIMARY KEY (user_id, category))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS donations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT,amount TEXT,image_url TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS maxicoins (user_id INT,amount INT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS available_cars (brand TEXT,model TEXT,config TEXT,year INTEGER,price INTEGER,body_type TEXT,transmission TEXT,engine TEXT,image_data TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS purchased_cars (id INTEGER PRIMARY KEY AUTOINCREMENT,brand TEXT,model TEXT,config TEXT,purchase_price INTEGER,buyer_id INTEGER,purchase_date TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS pts(car_id INTEGER,owner_id INTEGER,brand TEXT,model TEXT,config TEXT, color TEXT,body TEXT,transmission TEXT,plate_number TEXT,status TEXT,horsepower TEXT, photo_url TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS real_estate (id INTEGER PRIMARY KEY AUTOINCREMENT,buyer_id INTEGER DEFAULT NULL,address TEXT,price INTEGER,class TEXT,property_type TEXT,garage_slots INTEGER,square_meters INTEGER,house_photo_url TEXT,location_photo_url TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS rentcar (car_id INTEGER,owner_id INTEGER,renter_id INTEGER,start_time DATETIME,end_time DATETIME,price_per_hour INTEGER,total_price INTEGER,status TEXT,PRIMARY KEY (car_id, start_time))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS jobs_settings (id INTEGER PRIMARY KEY,jobs_enabled BOOLEAN NOT NULL DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY,name TEXT NOT NULL,hourly_pay INTEGER NOT NULL,is_government BOOLEAN NOT NULL,required_license TEXT,required_driving_hours INTEGER DEFAULT 0,role_id TEXT,promotion_role_name TEXT, promotion_role_id TEXT, promotion_time_hours INTEGER DEFAULT 0, employability INTEGER DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS user_jobs (user_id INTEGER NOT NULL,job_id INTEGER NOT NULL,start_time TEXT NOT NULL,worked_hours REAL DEFAULT 0,FOREIGN KEY (job_id) REFERENCES jobs(id))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS addjobs (job_id INTEGER,vehicle_config_url TEXT,spawn_location_url TEXT,car TEXT,PRIMARY KEY (job_id),FOREIGN KEY (job_id) REFERENCES jobs(id))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS active_shifts (user_id INTEGER PRIMARY KEY,job_id INTEGER,start_time TEXT,FOREIGN KEY (job_id) REFERENCES jobs(id))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS promotion_notifications (user_id TEXT,job_id INTEGER,notification_time TEXT,PRIMARY KEY (user_id, job_id))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS hotel_bookings (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,start_date TEXT NOT NULL,end_date TEXT NOT NULL,days INTEGER NOT NULL,total_price INTEGER NOT NULL)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS marketplace (id INTEGER PRIMARY KEY AUTOINCREMENT,seller_id INTEGER NOT NULL,item_name TEXT NOT NULL,item_type TEXT NOT NULL,item_id TEXT,price INTEGER NOT NULL,description TEXT, image_url TEXT,created_at TEXT NOT NULL,status TEXT DEFAULT 'active')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS medals (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,medal_type TEXT NOT NULL,award_date TEXT NOT NULL)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS car_service_requests (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,car_id INTEGER NOT NULL,brand TEXT NOT NULL,model TEXT NOT NULL,config TEXT NOT NULL,damage_description TEXT,photo_front TEXT,photo_back TEXT,photo_left TEXT,photo_right TEXT,status TEXT NOT NULL,thread_id INTEGER,created_at TEXT NOT NULL,completed_at TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS car_tuning_requests (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,car_id INTEGER,brand TEXT,model TEXT,config TEXT,tuning_description TEXT,photo_front TEXT,photo_back TEXT,photo_left TEXT,photo_right TEXT,status TEXT,thread_id INTEGER,created_at TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tire_service_requests (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,car_id INTEGER,brand TEXT,model TEXT,config TEXT,service_type TEXT,service_description TEXT,photo_wheels TEXT,photo_tires TEXT,status TEXT,thread_id INTEGER,created_at TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS service_invoices (id INTEGER PRIMARY KEY AUTOINCREMENT,service_type TEXT,request_id INTEGER,user_id INTEGER,amount INTEGER,status TEXT DEFAULT 'pending',issued_by INTEGER,issued_at TEXT,paid_at TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS traffic_violations (id INTEGER PRIMARY KEY AUTOINCREMENT,violator_id INTEGER NOT NULL,officer_id INTEGER NOT NULL,violation_details TEXT NOT NULL,impounded_car_id INTEGER,license_revoked BOOLEAN NOT NULL DEFAULT 0,fine_amount INTEGER NOT NULL DEFAULT 0,issued_at TEXT NOT NULL,thread_id INTEGER,status TEXT DEFAULT 'active')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS loans (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,principal_amount INTEGER NOT NULL,remaining_amount INTEGER NOT NULL,interest_rate REAL NOT NULL DEFAULT 0.1,start_date TEXT NOT NULL,last_payment_date TEXT,next_payment_date TEXT NOT NULL,payment_periods INTEGER NOT NULL, remaining_periods INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active', penalty_amount INTEGER DEFAULT 0,overdue_days INTEGER DEFAULT 0,purpose TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS garage_slots (id INTEGER PRIMARY KEY AUTOINCREMENT,owner_id INTEGER,slots INTEGER DEFAULT 1,purchase_date TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS driving_exams (id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL,instructor_id INTEGER NOT NULL,category TEXT NOT NULL,status TEXT NOT NULL,result TEXT,start_time TEXT NOT NULL,end_time TEXT)''')
conn.commit()


BEAMMP_MODERATORS = ["Pacetten007", "Dewerto", "haitu55", "Chepard22", "Fellisia", "Sanya_Dolg"]  

cursor.execute('SELECT COUNT(*) FROM jobs_settings')
if cursor.fetchone()[0] == 0:
    cursor.execute('INSERT OR IGNORE INTO jobs_settings (id, jobs_enabled) VALUES (1, 0)')
    conn.commit()

ADMIN_ID = 1051764411578191872
current_donator = None 

def check_license_status(issue_date):
    expiration_date = datetime.fromisoformat(issue_date) + timedelta(days=90)
    return 'Действительны' if datetime.now() < expiration_date else 'Просрочены'



@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} запущен!')
    channel = bot.get_channel(1346840187950338210)
    async for message in channel.history():
        if message.author == bot.user and message.components:
            await message.delete()
    embed = disnake.Embed(
        title="🚗 Регистрация транспортных средств",
        description="Нажмите на кнопку ниже, чтобы начать процесс регистрации вашего транспортного средства",
        color=disnake.Color.blue()
    )
    view = disnake.ui.View(timeout=None)
    view.add_item(AddPTSButton())
    await channel.send(embed=embed, view=view)
    await starting()

class AddPTSButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(
            label="Создать тикет",
            style=disnake.ButtonStyle.primary,
            emoji="🚗",
            custom_id="register_vehicle"
        )

    async def callback(self, inter: disnake.MessageInteraction):
        modal = PTSModal(inter.author)
        await inter.response.send_modal(modal)




async def команды(ctx):
    """Displays all available commands organized by categories"""
    try:
        # Define command categories
        categories = {
            "🚗 Автомобили": [
                ("!автосалон", "Купить автомобиль"),
                ("!гараж", "Просмотр ваших автомобилей"),
                ("!продать_авто id @игрок цена", "Продать автомобиль"),
                ("!аренда", "Арендовать автомобиль"),
                ("!авто id", "Просмотр автомобиля"),
                ("!птс id", "Просмотр птс автомобиля"),
                ("!продать_автогос id", "Продать автомобиль в государство"),
                ("!аренда_авто id @игрок цена-в-час часы", "Сдать автомобиль в аренду"),
                ("!мои_аренды", "Просмотр ваших арендованных автомобилей"),
                ("!мои_права", "Просмотр ваших прав"),
            ],
            "💼 Работа": [
                ("!трудоустройство", "Найти работу"),
                ("!мои_работы", "Просмотр ваших работ, а так же возможность уволиться"),
                ("!начать_работу", "Начать рабочую смену"),
                ("!конец_работы", "Закончить рабочую смену"),
                ("!смена", "Просмотр текущей смены")
            ],
            "💰 Экономика": [
                ("!bal", "Проверить ваш баланс"),
                ("!pay @игрок", "Перевести деньги другому игроку"),
                ("!top", "Показать топ игроков по балансу"),
            ],
            "🏠 Недвижимость": [
                ("!недвижимость", "Купить дом,гараж и другую недвижимость"),
                ("!мои_дома", "Просмотр ваших домов"),
                ("!продать_дом", "Продать дом"),
                ("!гаражные места", "Посмотреть свои гаражные места"),
                ("!продать_дом id @игрок цена", "Продать дом игроку"),
                ("!продать_домгос id", "Продать дом государству"),
                ("!моя_недвижимость", "Посмотреть свою недвижимость"),
                ("!объект id", "Посмотреть детали недвижимости"),
                ("!отель кол-во дней", "Забронировать отель"),
                ("!мой_отель", "Посмотреть свою комнату в отеле")
                
            ],
            "💰 Донат": [
                ("!donat", "Оформить донат"),
                ("!donatbal", "Посмотреть баланс Maxi Coins"),
                ("!top", "Показать топ игроков по балансу"),
                ("!купить_валюту", "Купить игровую валюту за Maxi Coins"),
                ("!купить_гараж", "Купить гаражное место за Maxi Coins")
            ]
        }
        
        # Start with the general category
        current_category = "💰 Донат"
        
        # Function to create embed for a specific category
        async def create_category_embed(category_name):
            embed = disnake.Embed(
                title="📚 Список команд",
                description=f"**Категория: {category_name}**\n\n",
                color=disnake.Color.blue()
            )
            
            # Add commands for this category
            commands_list = categories.get(category_name, [])
            for cmd, desc in commands_list:
                embed.description += f"**{cmd}** - {desc}\n"
            
            embed.set_footer(text="Используйте кнопки ниже для навигации по категориям")
            return embed
        
        # Create view with category buttons
        view = disnake.ui.View(timeout=300)  # 5 minute timeout
        
        # Create buttons for each category
        for category_name in categories.keys():
            button = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label=category_name,
                custom_id=f"category_{category_name}"
            )
            
            async def button_callback(interaction, category=category_name):
                if interaction.author.id != ctx.author.id:
                    return await interaction.response.send_message("Это не ваше меню команд!", ephemeral=True)
                
                embed = await create_category_embed(category)
                await interaction.response.edit_message(embed=embed)
            
            button.callback = button_callback
            view.add_item(button)
        
        # Initial embed
        initial_embed = await create_category_embed(current_category)
        
        # Send the message with the view
        await ctx.send(embed=initial_embed, view=view)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при отображении команд: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)


@bot.slash_command(name="донат", description="Управление донатами и Maxi-Coins")
async def donation_commands(inter: ApplicationCommandInteraction):
    """Группа команд для управления донатами и Maxi-Coins"""
    pass

@donation_commands.sub_command(name="пополнить", description="Пополнить игровой баланс")
async def donate(inter: ApplicationCommandInteraction):
    """Пополнить игровой баланс через донат"""
    global current_donator
    current_donator = inter.author.id  

    logging.info(f"{inter.author} initiated a donation process.")

    embed = disnake.Embed(
        title="💰 Пополнение игрового баланса",
        description="🎮 Добро пожаловать в систему пополнения!\n\n"
                    "💎 Вы можете приобрести донат-валюту, которую можно обменять на различные услуги и предметы или же игровые деньги по определенному курсу.\n",
        color=disnake.Color.gold()
    )
    embed.add_field(
        name="💳 Способы оплаты:",
        value="• Тинькофф Банк\n• DonationAlerts (для зарубежных стран)",
        inline=False
    )
    embed.add_field(name="", value="**Для продолжения напишите сумму пополнения цифрами в личные сообщения боту**\n\n")
    embed.set_footer(text="Текущий курс: 1 Maxi-Coin = 2,800 игровой валюты")
    
    await inter.response.send_message("✅ Проверьте личные сообщения для продолжения процесса пополнения", ephemeral=True)
    await inter.author.send(embed=embed)

    def check(msg):
        return msg.author == inter.author and isinstance(msg.channel, disnake.DMChannel)

    try:
        response = await bot.wait_for('message', check=check, timeout=300)

        if response.content.isdigit():
            amount = response.content
            await inter.author.send(f"Реквизиты (Т-банк) - https://www.tinkoff.ru/rm/r_sDpUdUUONT.bpJcZEymPM/LuA7Z57177\n"
                                  f"Реквизиты (Зарубежные страны. Когда используете платформу,пишите имя схожее с тегом дискорда!) - https://www.donationalerts.com/r/splug_team_project\n"
                                  f"Получатель - Никита Л.\n"
                                  f"Описание - после оплаты, отправьте сюда чек оплаты в виде скриншота.")

            def check_image(msg):
                return msg.author == inter.author and isinstance(msg.channel, disnake.DMChannel) and msg.attachments

            while True:
                try:
                    image_msg = await bot.wait_for('message', check=check_image, timeout=300)
                    if image_msg.attachments:
                        image_url = image_msg.attachments[0].url
                        cursor.execute('INSERT INTO donations (user_id, amount, image_url) VALUES (?, ?, ?)', 
                                       (inter.author.id, amount, image_url))
                        conn.commit()
                        donation_id = cursor.lastrowid
                        channel_id = 1343156587786928158  
                        channel = bot.get_channel(channel_id)
                        embed = disnake.Embed(title="Новый донат",
                                              description=f"Донат от {inter.author.mention}",
                                              colour=disnake.Color.dark_embed())
                        embed.add_field(name="ID доната:", value=donation_id)
                        embed.add_field(name="Сумма:", value=f'{amount}₽')
                        embed.set_image(url=image_url)                        
                        await channel.send(embed=embed)
                        await inter.author.send("Ожидайте проверки и выдачи валюты. Свяжитесьтр с crosshair0972(Sky), чтобы админисации было удобнее с выдачей товара.")
                        break
                except asyncio.TimeoutError:
                    await inter.author.send("Время ожидания истекло. Пожалуйста, начните процесс заново.")
                    return
        else:
            await inter.author.send("Пожалуйста, введите только цифры.")

    except asyncio.TimeoutError:
        await inter.author.send("Время ожидания истекло. Пожалуйста, начните процесс заново.")

@donation_commands.sub_command(name="баланс", description="Проверить баланс Maxi-Coins")
async def donation_balance(inter: ApplicationCommandInteraction):
    """Проверить баланс Maxi-Coins"""
    user_id = inter.author.id  
    cursor.execute('SELECT amount FROM maxicoins WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        amount = result[0]
    else:
        amount = 0
    embed = disnake.Embed(
        title="💰 Баланс Maxi-Coins",
        description=f"У вас на счету: **{amount}** Maxi-Coins",
        color=disnake.Color.gold()
    )
    embed.set_footer(text="Спасибо за поддержку проекта!")
    await inter.response.send_message(embed=embed, ephemeral=True)

@donation_commands.sub_command(name="купить_валюту", description="Купить игровую валюту за Maxi-Coins")
async def buy_currency(inter: ApplicationCommandInteraction, amount: int):
    """Купить игровую валюту за Maxi-Coins"""
    await inter.response.defer(ephemeral=True)
    user_id = inter.author.id
        
    # Проверяем, есть ли у пользователя достаточное количество донат-валюты
    cursor.execute('SELECT amount FROM maxicoins WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    if result and result[0] >= amount:
        bal = unbclient.get_user_bal(1341469479510474813, int(user_id))
        new_bal = bal['cash'] + amount * 2800
        unbclient.set_user_bal(1341469479510474813, int(user_id), cash=new_bal)

        # Обновляем баланс донат-валюты
        new_balance = result[0] - amount
        cursor.execute('UPDATE maxicoins SET amount = ? WHERE user_id = ?', (new_balance, user_id))
        conn.commit()

        embed = disnake.Embed(
            title="💰 Успешная конвертация",
            description=f"Вы успешно обменяли донат-валюту на игровую валюту!",
            color=disnake.Color.green()
        )
        embed.add_field(
            name="📊 Детали операции",
            value=f"**Конвертировано:** {amount} Maxi-Coins\n"
                  f"**Получено:** {amount * 2800} игровой валюты",
            inline=False
        )
        embed.add_field(
            name="💎 Ваш баланс",
            value=f"**Maxi-Coins:** {new_balance}",
            inline=False
        )
        embed.set_footer(text="Спасибо за использование нашего сервиса!")
        
        await inter.edit_original_response(embed=embed)
    else:
        await inter.edit_original_response(content="У вас недостаточно донат-валюты для выполнения этого перевода.")

@donation_commands.sub_command(name="купить_гараж", description="Купить гаражные места за Maxi-Coins")
async def buy_garage(inter: ApplicationCommandInteraction, slots: int = 1):
    """Купить дополнительные гаражные места за Maxi-Coins"""
    await inter.response.defer(ephemeral=True)
    try:
        # Check if user already has garage slots
        cursor.execute('SELECT slots FROM garage_slots WHERE owner_id = ?', (inter.author.id,))
        result = cursor.fetchone()
        cost = 0
        for i in range(slots):
            if i == 0:
                cost += 115
            elif i == 1:
                cost += 220
            elif i == 2:
                cost += 330
            else:
                cost += 110
        
        # Check user's Maxi-Coins balance
        cursor.execute('SELECT amount FROM maxicoins WHERE user_id = ?', (inter.author.id,))
        balance = cursor.fetchone()
        
        if not balance or balance[0] < cost:
            embed = disnake.Embed(
                title="❌ Недостаточно Maxi-Coins",
                description=f"Необходимо: {cost} Maxi-Coins\nУ вас: {balance[0] if balance else 0} Maxi-Coins",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
            
        # Update or insert garage slots
        if result:
            new_slots = result[0] + slots
            cursor.execute('UPDATE garage_slots SET slots = ? WHERE owner_id = ?', 
                         (new_slots, inter.author.id))
        else:
            cursor.execute('INSERT INTO garage_slots (owner_id, slots, purchase_date) VALUES (?, ?, ?)',
                         (inter.author.id, slots, datetime.now().isoformat()))
                         
        # Deduct Maxi-Coins
        new_balance = balance[0] - cost
        cursor.execute('UPDATE maxicoins SET amount = ? WHERE user_id = ?',
                      (new_balance, inter.author.id))
        
        conn.commit()
        
        embed = disnake.Embed(
            title="✅ Гаражные места куплены",
            description=(
                "━━━━━━━━━━ Информация о покупке ━━━━━━━━━━\n\n"
                f"🏠 **Куплено мест:** {slots}\n"
                f"💰 **Стоимость:** {cost} Maxi-Coins\n"
                f"📊 **Всего мест:** {new_slots if result else slots}\n"
                f"💎 **Остаток Maxi-Coins:** {new_balance}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        embed.set_footer(text="Спасибо за поддержку проекта!")
        await inter.edit_original_response(embed=embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при покупке: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@donation_commands.sub_command_group(name="админ", description="Команды администрации для управления донатами")
async def donation_admin(inter: ApplicationCommandInteraction):
    """Группа команд администрации для управления донатами"""
    pass

@donation_admin.sub_command(name="принять", description="Принять донат")
@commands.has_role("High Stuff+")
async def accept_donation(inter: ApplicationCommandInteraction, donation_id: int):
    """Принять донат (только для администрации)"""
    await inter.response.defer(ephemeral=True)
    cursor.execute('SELECT user_id, amount, image_url FROM donations WHERE id = ?', (donation_id,))
    donation = cursor.fetchone()

    if donation:
        user_id, amount, image_url = donation
        user = await bot.fetch_user(user_id)

        embed = disnake.Embed(
            title="✅ Донат принят!",
            description=f"Ваш донат на сумму **{amount}₽** был успешно принят.",
            color=disnake.Color.green()
        )
        embed.add_field(
            name="💝 Благодарность",
            value="Спасибо за вашу поддержку! Мы очень ценим каждого донатера.",
            inline=False
        )
        await user.send(embed=embed)

        cursor.execute('SELECT amount FROM maxicoins WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if result:
            new_amount = result[0] + int(amount)
            cursor.execute('UPDATE maxicoins SET amount = ? WHERE user_id = ?', (new_amount, user_id))
        else:
            cursor.execute('INSERT INTO maxicoins (user_id, amount) VALUES (?, ?)', (user_id, amount))

        conn.commit()

        await inter.edit_original_response(content=f"Донат ID {donation_id} принят. Пользователь {user.mention} уведомлен.")
        
        cursor.execute('DELETE FROM donations WHERE id = ?', (donation_id,))
        conn.commit()
    else:
        await inter.edit_original_response(content=f"Донат с ID {donation_id} не найден.")

@donation_admin.sub_command(name="отклонить", description="Отклонить донат")
@commands.has_role("High Stuff+")
async def reject_donation(inter: ApplicationCommandInteraction, donation_id: int):
    """Отклонить донат (только для администрации)"""
    await inter.response.defer(ephemeral=True)
    cursor.execute('SELECT user_id, amount, image_url FROM donations WHERE id = ?', (donation_id,))
    donation = cursor.fetchone()

    if donation:
        user_id, amount, image_url = donation
        user = await bot.fetch_user(user_id)

        embed = disnake.Embed(
            title="❌ Донат отклонен",
            description=f"К сожалению, ваш донат на сумму **{amount}₽** был отклонен.",
            color=disnake.Color.red()
        )
        embed.add_field(
            name="📝 Что делать дальше?",
            value="Пожалуйста, свяжитесь с администрацией для получения дополнительной информации.",
            inline=False
        )
        await user.send(embed=embed)

        await inter.edit_original_response(content=f"Донат ID {donation_id} отклонен. Пользователь {user.mention} уведомлен.")
        
        cursor.execute('DELETE FROM donations WHERE id = ?', (donation_id,))
        conn.commit()
    else:
        await inter.edit_original_response(content=f"Донат с ID {donation_id} не найден.")


@bot.slash_command(name="гараж", description="Команды для управления гаражом")
async def garage_commands(inter: ApplicationCommandInteraction):
    """Группа команд для управления гаражом"""
    pass

@garage_commands.sub_command(name="места", description="Показать информацию о гаражных местах")
async def garage_slots(inter: ApplicationCommandInteraction):
    """Показывает информацию о гаражных местах"""
    try:
        await inter.response.defer()
        
        # Get real estate details with garage slots first
        cursor.execute('''
            SELECT address, garage_slots, id, property_type 
            FROM real_estate 
            WHERE buyer_id = ? AND garage_slots > 0
        ''', (inter.author.id,))
        properties = cursor.fetchall()
        
        # Get additional garage slots
        cursor.execute('SELECT slots, purchase_date FROM garage_slots WHERE owner_id = ?', 
                      (inter.author.id,))
        garage_result = cursor.fetchone()
        
        # Check for active hotel booking
        cursor.execute('''
            SELECT end_date FROM hotel_bookings
            WHERE user_id = ? AND end_date > ?
        ''', (inter.author.id, datetime.now().isoformat()))
        hotel_booking = cursor.fetchone()
        hotel_slots = 1 if hotel_booking else 0
        
        # Calculate total slots from real estate
        cursor.execute('SELECT SUM(garage_slots) FROM real_estate WHERE buyer_id = ?',
                      (inter.author.id,))
        estate_slots = cursor.fetchone()[0] or 0
        
        # Calculate total slots
        total_slots = (garage_result[0] if garage_result else 0) + estate_slots + hotel_slots
        
        if total_slots > 0:
            embed = disnake.Embed(
                title="🏠 Информация о гаражных местах",
                description=(
                    "━━━━━━━━━━ Ваши места ━━━━━━━━━━\n"
                    "🚘 Здесь отображаются все ваши гаражные места\n"
                    "✨ Включая места от недвижимости и дополнительные"
                ),
                color=disnake.Color.blue()
            )
            if properties:
                estate_details = "\n".join(
                    f"🏢 **{property_type} {address} (ID: {id_})**\n"
                    f"└─ • {slots} гаражное мест(а)"
                    for address, slots, id_, property_type in properties
                )
                embed.add_field(
                    name="🏘️ Недвижимость с гаражами\n",
                    value=estate_details,
                    inline=False
                )
            
            # Add additional garage slots info
            if garage_result:
                embed.add_field(
                    name="📅 Дополнительные гаражные места:",
                    value=f"Количество: {garage_result[0]}\nДата покупки: {datetime.fromisoformat(garage_result[1]).strftime('%d.%m.%Y')}",
                    inline=False
                )
            
            # Add hotel slot info if available
            if hotel_booking:
                end_date = datetime.fromisoformat(hotel_booking[0])
                embed.add_field(
                    name="🏨 Отель:",
                    value=f"Дополнительное место: 1\nДействует до: {end_date.strftime('%d.%m.%Y')}",
                    inline=False
                )
            
            # Add total slots info
            embed.add_field(
                name="📊 Общая информация:",
                value=f"Всего мест: {total_slots}\n• От недвижимости: {estate_slots}\n• Дополнительные: {garage_result[0] if garage_result else 0}\n• От отеля: {hotel_slots}",
                inline=False
            )
            
            embed.description += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
        else:
            embed = disnake.Embed(
                title="🏠 Информация о гаражных местах",
                description="У вас нет гаражных мест\nИспользуйте команду /гараж купить для покупки или приобретите недвижимость с гаражом",
                color=disnake.Color.orange()
            )
            
        await inter.edit_original_response(embed=embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при проверке мест: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)
        
@bot.slash_command(name="права", description="Управление водительскими правами")
async def license_commands(inter: ApplicationCommandInteraction):
    """Группа команд для управления водительскими правами"""
    pass

@license_commands.sub_command(name="мои", description="Показать ваши водительские права")
async def my_licenses(inter: ApplicationCommandInteraction):
    """Показывает ваши водительские права"""
    user_id = str(inter.author.id)
    cursor.execute('SELECT category, issue_date FROM licenses WHERE user_id = ?', (user_id,))
    licenses_info = cursor.fetchall()
    
    if licenses_info:
        licenses_per_embed = 5
        total_licenses = len(licenses_info)
        num_embeds = (total_licenses + licenses_per_embed - 1) // licenses_per_embed

        for embed_index in range(num_embeds):
            start_idx = embed_index * licenses_per_embed
            end_idx = min(start_idx + licenses_per_embed, total_licenses)
            current_licenses = licenses_info[start_idx:end_idx]

            embed = disnake.Embed(
                title="🚗 Водительское удостоверение",
                description=f"**Владелец:** {inter.author.mention}\n" + 
                          f"**Номер удостоверения:** {inter.author.id}\n" +
                          "━━━━━━━━━━━━━━━━━━━━━━━",
                color=disnake.Color.brand_green()
            )

            # Add license categories to current embed
            for category, issue_date in current_licenses:
                status = check_license_status(issue_date)
                date = datetime.fromisoformat(issue_date).date()
                expiration_date = (datetime.fromisoformat(issue_date) + timedelta(days=90)).date()
                
                status_emoji = "✅" if status == "Действительны" else "❌"
                
                embed.add_field(
                    name=f"📝 Категория {category}",
                    value=f"```\n"
                          f"Статус: {status_emoji} {status}\n"
                          f"Выдано: {date.strftime('%d.%m.%Y')}\n"
                          f"Действует до: {expiration_date.strftime('%d.%m.%Y')}\n"
                          f"```",
                    inline=False
                )

            # Add page number if multiple embeds
            if num_embeds > 1:
                embed.set_footer(text=f"ГИБДД | Единая база данных • Страница {embed_index + 1}/{num_embeds}")
            else:
                embed.set_footer(text="ГИБДД | Единая база данных")
            
            embed.timestamp = datetime.now()
            
            if embed_index == 0:
                await inter.response.send_message(embed=embed)
            else:
                await inter.followup.send(embed=embed)
    else:
        error_embed = disnake.Embed(
            title="❌ Водительские удостоверения не найдены",
            description="У вас нет прав на управление транспортным средством.\n" +
                       "Для получения прав обратитесь в автошколу.",
            color=disnake.Color.red()
        )
        error_embed.set_footer(text="ГИБДД | Единая база данных")
        await inter.response.send_message(embed=error_embed)

@license_commands.sub_command(name="проверить", description="Проверить права другого игрока")
async def check_licenses(inter: ApplicationCommandInteraction, member: disnake.Member):
    """Проверяет права другого игрока (только для ГИБДД)"""
    if not any(role.name == "ГИБДД" for role in inter.author.roles):
        await inter.response.send_message("У вас нет доступа к этой команде!", ephemeral=True)
        return
        
    user_id = str(member.id)
    cursor.execute('SELECT category, issue_date FROM licenses WHERE user_id = ?', (user_id,))
    licenses_info = cursor.fetchall()
    
    if licenses_info:
        embed = disnake.Embed(
            title="🚗 Водительское удостоверение",
            description=f"**Владелец:** {member.mention}\n" + 
                      f"**Номер удостоверения:** {member.id}\n" +
                      "━━━━━━━━━━━━━━━━━━━━━━━",
            color=disnake.Color.brand_green()
        )
        
        for category, issue_date in licenses_info:
            status = check_license_status(issue_date)
            date = datetime.fromisoformat(issue_date).date()
            expiration_date = (datetime.fromisoformat(issue_date) + timedelta(days=90)).date()
            
            status_emoji = "✅" if status == "Действительны" else "❌"
            
            embed.add_field(
                name=f"📝 Категория {category}",
                value=f"```\n"
                      f"Статус: {status_emoji} {status}\n"
                      f"Выдано: {date.strftime('%d.%m.%Y')}\n"
                      f"Действует до: {expiration_date.strftime('%d.%m.%Y')}\n"
                      f"```",
                inline=False
            )
        
        embed.set_footer(text="ГИБДД | Единая база данных")
        embed.timestamp = datetime.now()
        await inter.response.send_message(embed=embed)
    else:
        await inter.response.send_message(f"У участника {member.display_name} нет прав на управление транспортным средством.")

@license_commands.sub_command(name="лишить", description="Лишить игрока водительских прав")
async def revoke_licenses(inter: ApplicationCommandInteraction, member: disnake.Member):
    """Лишает игрока водительских прав (только для ГИБДД)"""
    if not any(role.name == "ГИБДД" for role in inter.author.roles):
        await inter.response.send_message("У вас нет доступа к этой команде!", ephemeral=True)
        return
        
    user_id = str(member.id)
    cursor.execute('DELETE FROM licenses WHERE user_id = ?', (user_id,))
    conn.commit()
    
    embed = disnake.Embed(
        title="🚫 Лишение прав",
        description=(
            "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
            f"👤 **Гражданин:** {member.mention}\n"
            f"📝 **Статус:** {'Права изъяты' if cursor.rowcount > 0 else 'Прав не имеет'}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=disnake.Color.red() if cursor.rowcount > 0 else disnake.Color.orange()
    )
    embed.set_footer(text="ГИБДД | Единая база данных")
    embed.timestamp = datetime.now()
    await inter.response.send_message(embed=embed)

@license_commands.sub_command(name="выдать_a", description="Выдать права категории A")
async def add_license_a(inter: ApplicationCommandInteraction, member: disnake.Member):
    """Выдает права категории A (только для инструкторов)"""
    if not any(role.name == "Инструктор категории A" for role in inter.author.roles):
        await inter.response.send_message("У вас нет доступа к этой команде!", ephemeral=True)
        return
        
    user_id = str(member.id)
    cursor.execute('INSERT OR REPLACE INTO licenses (user_id, category, issue_date) VALUES (?, ?, ?)', 
                   (user_id, 'A', datetime.now().isoformat()))
    conn.commit()
    
    embed = disnake.Embed(
        title="🏍️ Выдача водительского удостоверения",
        description=(
            "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
            f"👤 **Получатель:** {member.mention}\n"
            f"📝 **Категория:** A\n"
            f"📅 **Дата выдачи:** {datetime.now().strftime('%d.%m.%Y')}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=disnake.Color.green()
    )
    embed.set_footer(text="ГИБДД | Единая база данных")
    embed.timestamp = datetime.now()
    await inter.response.send_message(embed=embed)

@license_commands.sub_command(name="выдать_b", description="Выдать права категории B")
async def add_license_b(inter: ApplicationCommandInteraction, member: disnake.Member):
    """Выдает права категории B (только для инструкторов)"""
    if not any(role.name == "Инструктор категории B" for role in inter.author.roles):
        await inter.response.send_message("У вас нет доступа к этой команде!", ephemeral=True)
        return
        
    user_id = str(member.id)
    cursor.execute('INSERT OR REPLACE INTO licenses (user_id, category, issue_date) VALUES (?, ?, ?)', 
                   (user_id, 'B', datetime.now().isoformat()))
    conn.commit()
    
    embed = disnake.Embed(
        title="🚗 Выдача водительского удостоверения",
        description=(
            "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
            f"👤 **Получатель:** {member.mention}\n"
            f"📝 **Категория:** B\n"
            f"📅 **Дата выдачи:** {datetime.now().strftime('%d.%m.%Y')}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=disnake.Color.green()
    )
    embed.set_footer(text="ГИБДД | Единая база данных")
    embed.timestamp = datetime.now()
    await inter.response.send_message(embed=embed)

@license_commands.sub_command(name="выдать_c", description="Выдать права категории C")
async def add_license_c(inter: ApplicationCommandInteraction, member: disnake.Member):
    """Выдает права категории C (только для инструкторов)"""
    if not any(role.name == "Инструктор категории C" for role in inter.author.roles):
        await inter.response.send_message("У вас нет доступа к этой команде!", ephemeral=True)
        return
    user_id = str(member.id)
    cursor.execute('INSERT OR REPLACE INTO licenses (user_id, category, issue_date) VALUES (?, ?, ?)', 
                   (user_id, 'C', datetime.now().isoformat()))
    conn.commit()
    embed = disnake.Embed(
        title="🚛 Выдача водительского удостоверения",
        description=(
            "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
            f"👤 **Получатель:** {member.mention}\n"
            f"📝 **Категория:** C\n"
            f"📅 **Дата выдачи:** {datetime.now().strftime('%d.%m.%Y')}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=disnake.Color.green()
    )
    embed.set_footer(text="ГИБДД | Единая база данных")
    embed.timestamp = datetime.now()
    await inter.response.send_message(embed=embed)

@license_commands.sub_command(name="выдать_d", description="Выдать права категории D")
async def add_license_d(inter: ApplicationCommandInteraction, member: disnake.Member):
    """Выдает права категории D (только для инструкторов)"""
    if not any(role.name == "Инструктор категории D" for role in inter.author.roles):
        await inter.response.send_message("У вас нет доступа к этой команде!", ephemeral=True)
        return
        
    user_id = str(member.id)
    cursor.execute('INSERT OR REPLACE INTO licenses (user_id, category, issue_date) VALUES (?, ?, ?)', 
                   (user_id, 'D', datetime.now().isoformat()))
    conn.commit()
    
    embed = disnake.Embed(
        title="🚌 Выдача водительского удостоверения",
        description=(
            "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
            f"👤 **Получатель:** {member.mention}\n"
            f"📝 **Категория:** D\n"
            f"📅 **Дата выдачи:** {datetime.now().strftime('%d.%m.%Y')}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=disnake.Color.green()
    )
    embed.set_footer(text="ГИБДД | Единая база данных")
    embed.timestamp = datetime.now()
    await inter.response.send_message(embed=embed)

async def starting():
    """Initialize background tasks"""
    check_server_status.start()
    check_rentals.start()
    check_promotion_eligibility.start()
    check_hotel_bookings.start()
    print("All background tasks started successfully")




@bot.command()
@commands.has_role('ГИБДД')
async def принять_птс(ctx, vehicle_id: int):
    cursor.execute('UPDATE pts SET status = "approved" WHERE car_id = ?', (vehicle_id,))
    conn.commit()
    
    if cursor.rowcount > 0:
        cursor.execute('SELECT owner_id FROM pts WHERE car_id = ?', (vehicle_id,))
        owner_id = cursor.fetchone()[0]
        owner = await bot.fetch_user(owner_id)
        embed = disnake.Embed(
            title="✅ ПТС одобрен!",
            description=(
                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                f"🔑 **ID автомобиля:** `{vehicle_id}`\n"
                "📝 Ваша заявка на регистрацию ТС была успешно одобрена!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        embed.set_footer(text="ГИБДД | Регистрационная база данных")
        embed.timestamp = datetime.now()
        await owner.send(embed=embed)
        await ctx.send(f"ПТС #{vehicle_id} одобрен")
        await pts(ctx, vehicle_id)
    else:
        await ctx.send("ПТС с таким ID не найден")

@bot.command()
@commands.has_role('ГИБДД')
async def отклонить_птс(ctx, vehicle_id: int, *, reason: str):
    cursor.execute('SELECT owner_id FROM pts WHERE car_id = ? AND status = "pending"', (vehicle_id,))
    result = cursor.fetchone()
    
    if result:
        owner_id = result[0]
        owner = await bot.fetch_user(owner_id)
        cursor.execute('DELETE FROM pts WHERE car_id = ?', (vehicle_id,))
        conn.commit()
        
        embed = disnake.Embed(
            title="❌ Заявка отклонена",
            description=(
                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                f"🔑 **ID заявки:** `{vehicle_id}`\n"
                f"📝 **Причина отказа:** {reason}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.red()
        )
        embed.set_footer(text="ГИБДД | Регистрационная база данных")
        embed.timestamp = datetime.now()
        await owner.send(embed=embed)
        await ctx.send(f"ПТС #{vehicle_id} отклонен")
    else:
        await ctx.send("ПТС с таким ID не найден или уже обработан")


class PTSModal(disnake.ui.Modal):
    def __init__(self, member):
        self.member = member
        components = [
            disnake.ui.TextInput(
                label="ID автомобиля",
                placeholder="Например: 72", 
                custom_id="car_id",
                required=True
            ),
            disnake.ui.TextInput(
                label="Цвет",
                placeholder="Например: Черный металлик",
                custom_id="color",
                required=True
            ),
            disnake.ui.TextInput(
                label="Лошадиные силы",
                placeholder="Например: 450",
                custom_id="horsepower",
                required=True
            )
        ]
        super().__init__(
            title="Регистрация транспортного средства",
            components=components,
            custom_id="pts_modal"
        )

    async def callback(self, inter: disnake.ModalInteraction):
        # Send a nicely formatted processing message
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_response(
            embed=disnake.Embed(
                title="⏳ Обработка заявки", 
                description="Пожалуйста, подождите...",
                color=disnake.Color.blue()
            )
        )
        
        car_id = inter.text_values["car_id"]
        
        # Check if PTS already exists or is pending
        cursor.execute('''
            SELECT status FROM pts 
            WHERE car_id = ? AND owner_id = ?
        ''', (car_id, self.member.id))
        
        existing_pts = cursor.fetchone()
        
        if existing_pts:
            status_messages = {
                'pending': 'ℹ️ Заявка на регистрацию ПТС для этого автомобиля находится на рассмотрении',
                'approved': 'ℹ️ Этот автомобиль уже имеет действующий ПТС'
            }
            # Send informational message only visible to the interaction user
            info_embed = disnake.Embed(
                title="ℹ️ Информация",
                description=status_messages.get(existing_pts[0], 'ℹ️ Этот автомобиль уже имеет ПТС'),
                color=disnake.Color.blue()
            )
            info_embed.set_footer(text="Сообщение от службы оформления ПТС")
            await inter.author.send(embed=info_embed)
            return
        
        # Get car info from purchased_cars
        cursor.execute('''
            SELECT brand, model, config, purchase_price 
            FROM purchased_cars 
            WHERE id = ? AND buyer_id = ?
        ''', (car_id, self.member.id))
        
        purchased_car = cursor.fetchone()
        
        if not purchased_car:
            error_embed = disnake.Embed(
                title="❌ Ошибка",
                description="Автомобиль с указанным ID не найден в вашем гараже!",
                color=disnake.Color.red()
            )
            error_embed.set_footer(text="Сообщение от службы оформления ПТС")
            await inter.author.send(embed=error_embed)
            return
            
        brand, model, config, price = purchased_car
        
        # Get additional car info from available_cars
        cursor.execute('''
            SELECT body_type, transmission, engine
            FROM available_cars 
            WHERE brand = ? AND model = ? AND config = ?
        ''', (brand, model, config))
        
        car_details = cursor.fetchone()
        
        if not car_details:
            error_embed = disnake.Embed(
                title="❌ Ошибка",
                description="Не удалось найти информацию об автомобиле!",
                color=disnake.Color.red()
            )
            error_embed.set_footer(text="Сообщение от службы оформления ПТС")
            await inter.author.send(embed=error_embed)
            return
            
        body_type, transmission, engine = car_details

        # Generate random plate number
        plate_number = f"{random.choice(['А', 'В', 'Е', 'К', 'М', 'Н', 'О', 'Р', 'С', 'Т', 'У', 'Х'])}{random.randint(100, 999)}{random.choice(['А', 'В', 'Е', 'К', 'М', 'Н', 'О', 'Р', 'С', 'Т', 'У', 'Х'])}{random.choice(['А', 'В', 'Е', 'К', 'М', 'Н', 'О', 'Р', 'С', 'Т', 'У', 'Х'])}|86"

        # Ask user to send photo
        await inter.author.send(
            "📸 Пожалуйста, отправьте фотографию автомобиля, на которой видны лошадиные силы и цвет."
        )
            
        def check(m):
            return m.author.id == self.member.id and m.attachments

        try:
            # Wait for photo
            photo_message = await bot.wait_for('message', check=check, timeout=300)
            
            # Get photo URL
            photo_url = photo_message.attachments[0].url

            # Send photo to approval channel
            photo_channel = bot.get_channel(1351431079738867763)
            photo_embed = await photo_channel.send(file=await photo_message.attachments[0].to_file())
            stored_photo_url = photo_embed.attachments[0].url

            # Insert into pts table
            cursor.execute('''
                INSERT INTO pts (
                    car_id, owner_id, brand, model, config, color,
                    body, transmission, plate_number, status, horsepower, photo_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            ''', (
                car_id, self.member.id, brand, model, config,
                inter.text_values["color"], body_type, transmission,
                plate_number, inter.text_values["horsepower"], stored_photo_url
            ))
            conn.commit()

            approval_channel = bot.get_channel(1346841023849955459)
            embed = disnake.Embed(
                title="📝 Новая заявка на регистрацию ТС",
                description=f"**Заявка № {car_id}**\n━━━━━━━━━━━━━━━━━━━━━━━━",
                color=disnake.Color.gold()
            )

            embed.add_field(
                name="👤 Владелец",
                value=f"{self.member.mention}\nID: {self.member.id}",
                inline=False
            )

            embed.add_field(
                name="🚗 Информация о ТС",
                value=f"**Марка:** {brand}\n"
                    f"**Модель:** {model}\n"
                    f"**Комплектация:** {config}\n"
                    f"**Цвет:** {inter.text_values['color']}\n"
                    f"**Мощность:** {inter.text_values['horsepower']} л.с.",
                inline=True
            )

            embed.add_field(
                name="⚙️ Дополнительные данные",
                value=f"**Тип кузова:** {body_type}\n"
                    f"**КПП:** {transmission}\n"
                    f"**Двигатель:** {engine}\n"
                    f"**Госномер:** `{plate_number}`\n"
                    f"**ID ТС:** {car_id}",
                inline=True
            )

            embed.set_image(url=stored_photo_url)
            embed.set_footer(text="Для обработки используйте команды !принять_птс или !отклонить_птс причина")
            embed.timestamp = datetime.now()

            await approval_channel.send(embed=embed)
            await self.member.send(
                "✅ Ваша заявка на регистрацию ТС успешно отправлена на рассмотрение!"
            )

        except asyncio.TimeoutError:
            await self.member.send("⚠️ Время ожидания фотографии истекло. Пожалуйста, начните процесс регистрации заново.")

@bot.command()
async def птс(ctx, vehicle_id: int):
    cursor.execute('''SELECT * FROM pts WHERE car_id = ?''', (vehicle_id,))
    vehicle = cursor.fetchone()
    
    if vehicle:
        if vehicle[9] == "pending":
            pending_embed = disnake.Embed(
                title="⏳ ПТС в обработке",
                description="Ваша заявка на регистрацию транспортного средства находится на рассмотрении.",
                color=disnake.Color.yellow()
            )
            await ctx.send(embed=pending_embed)
            return
            
        owner = await bot.fetch_user(vehicle[1])
        embed = disnake.Embed(
            title="🚗 Паспорт транспортного средства",
            description=f"Документ №{vehicle[0]}",
            color=disnake.Color.dark_blue()
        )
        
        embed.add_field(
            name="👤 Информация о владельце",
            value=f"Владелец: {owner.mention}",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Информация о автомобиле",
            value=f"**Марка:** {vehicle[2]}\n"
                  f"**Модель:** {vehicle[3]}\n"
                  f"**Цвет:** {vehicle[5]}\n"
                  f"**Тип кузова:** {vehicle[6]}",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Дополнительные данные",
            value=f"**КПП:** {vehicle[7]}\n"
                  f"**Госномер:** `{vehicle[8]}`\n"
                  f"**Мощность:** {vehicle[10]} л.с.\n"
                  f"**ID ТС:** {vehicle[0]}",
            inline=True
        )
        if vehicle[11]:
            embed.set_image(url=vehicle[11])
        
        embed.set_footer(text="ГИБДД | Регистрационная база данных")
        embed.timestamp = datetime.now()
        
        await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(
            title="❌ Ошибка поиска",
            description="Автомобиль с таким ID не найден в базе данных",
            color=disnake.Color.red()
        )
        await ctx.send(embed=embed)


@bot.command()
@commands.has_role('ГИБДД')
async def изменить_номер(ctx, vehicle_id: int, new_plate_number: str):
    cursor.execute('UPDATE pts SET plate_number = ? WHERE car_id = ?', 
                  (new_plate_number, vehicle_id))
    conn.commit()
    
    if cursor.rowcount > 0:
        embed = disnake.Embed(
            title="✅ Номер изменен",
            description=(
                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                f"🚗 **ID автомобиля:** {vehicle_id}\n"
                f"🔢 **Новый номер:** `{new_plate_number}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        embed.set_footer(text="ГИБДД | Регистрационная база данных")
        embed.timestamp = datetime.now()
        await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(
            title="❌ Ошибка",
            description=(
                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                "🚫 Автомобиль с указанным ID не найден в базе данных\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.red()
        )
        embed.set_footer(text="ГИБДД | Регистрационная база данных")
        embed.timestamp = datetime.now()
        await ctx.send(embed=embed)
    

@bot.slash_command(name="автосалон", description="Просмотр доступных автомобилей в автосалоне")
async def car_dealership(inter: ApplicationCommandInteraction):
    """Показывает доступные модели автомобилей"""
    try:
        await inter.response.defer()
        
        initial_embed = disnake.Embed(  
            title="⌛ Загрузка автосалона...",
            description="Пожалуйста, подождите...",
            color=disnake.Color.blue()
        )
        message = await inter.edit_original_response(embed=initial_embed)
        
        cursor.execute('SELECT DISTINCT brand FROM available_cars')
        brands_raw = [row[0] for row in cursor.fetchall()] 
        brands = []
        for brand in brands_raw:
            if brand and len(brand.strip()) > 0 and len(brand.strip()) <= 100:
                brands.append(brand.strip())
            elif brand and len(brand.strip()) > 100:
                brands.append(brand.strip()[:97] + "...") 
        
        if not brands:
            embed = disnake.Embed(
                title="Автосалон", 
                description="🚫 В настоящее время автомобили отсутствуют в продаже",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        

        brands_per_page = 25
        total_brand_pages = (len(brands) + brands_per_page - 1) // brands_per_page
        current_brand_page = 0
            
        brand_models = {}
        for brand in brands:
            cursor.execute('SELECT DISTINCT model FROM available_cars WHERE brand LIKE ?', (brand.replace("...", "%"),))
            models_raw = [row[0] for row in cursor.fetchall()]
            valid_models = []
            for model in models_raw:
                if model and len(model.strip()) > 0 and len(model.strip()) <= 100:
                    valid_models.append(model.strip())
                elif model and len(model.strip()) > 100:
                    valid_models.append(model.strip()[:97] + "...")       
            brand_models[brand] = valid_models
        

        async def update_brand_page(page_num):
            start_idx = page_num * brands_per_page
            end_idx = min(start_idx + brands_per_page, len(brands))
            current_page_brands = brands[start_idx:end_idx]
            
            select = disnake.ui.Select(
                placeholder=f"Выберите марку (стр. {page_num+1}/{total_brand_pages})",
                options=[disnake.SelectOption(label=brand, value=brand) for brand in current_page_brands]
            )
            
            async def brand_callback(interaction):
                if interaction.message.id != message.id:
                    return                
                await interaction.response.defer()            
                brand = select.values[0]
                models = brand_models[brand]
                
                if not models:
                    embed = disnake.Embed(
                        title="Ошибка",
                        description="Модели для выбранной марки не найдены",
                        color=disnake.Color.red()
                    )
                    return await interaction.edit_original_response(embed=embed)
                

                models_per_page = 25
                total_model_pages = (len(models) + models_per_page - 1) // models_per_page
                current_model_page = 0
                

                cursor.execute('''SELECT model, config, year, price, body_type,
                               transmission, engine, image_data FROM available_cars
                               WHERE brand = ?''', (brand,))
                all_configs = {row[0]: [] for row in cursor.fetchall()}           
                
                cursor.execute('''SELECT model, config, year, price, body_type,
                               transmission, engine, image_data FROM available_cars
                               WHERE brand = ?''', (brand,))
                for row in cursor.fetchall():
                    model_name = row[0]
                    all_configs[model_name].append(row[1:])
                

                async def update_model_page(page_num):
                    start_idx = page_num * models_per_page
                    end_idx = min(start_idx + models_per_page, len(models))
                    current_page_models = models[start_idx:end_idx]
                    
                    model_select = disnake.ui.Select(
                        placeholder=f"Выберите модель (стр. {page_num+1}/{total_model_pages})",
                        options=[disnake.SelectOption(label=model) for model in current_page_models]
                    )
                    
                    async def model_callback(inter):
                        if inter.message.id != message.id:
                            return                    
                        await inter.response.defer()                
                        model = model_select.values[0]
                        configs = all_configs.get(model, [])
                        
                        if not configs:
                            embed = disnake.Embed(
                                title="Ошибка",
                                description="Конфигурации не найдены",
                                color=disnake.Color.red()
                            )
                            return await inter.edit_original_response(embed=embed)
                            
                        configs.sort(key=lambda x: x[2])
                        current_config_index = 0
                        total_configs = len(configs)
                        
                        async def show_config(config_index, interaction):
                            config = configs[config_index]
                            embed = disnake.Embed(
                                title=f"🚗 {brand} {model} {config[0]}",
                                description=(
                                    "━━━━━━━━━━ Характеристики ━━━━━━━━━━\n\n"
                                    f"📅 **Год выпуска:** {config[1]}\n"
                                    f"🏗️ **Тип кузова:** {config[3]}\n"
                                    f"🔄 **Трансмиссия:** {config[4]}\n"
                                    f"🔧 **Двигатель:** {config[5]}\n\n"
                                    "━━━━━━━━━━ Стоимость ━━━━━━━━━━\n"
                                    f"💰 **Цена:** {config[2]:,}₽\n"
                                ),
                                color=disnake.Color.gold()
                            )
                            embed.set_footer(text=f"📋 Конфигурация {config_index + 1} из {total_configs}")
                            if config[6]:
                                embed.set_image(url=config[6])

                            view = disnake.ui.View(timeout=180)
                            prev_button = disnake.ui.Button(
                                style=disnake.ButtonStyle.secondary,
                                label="◀️ Предыдущая",
                                custom_id="prev_config",
                                disabled=config_index == 0
                            )     
                            async def prev_callback(prev_inter):
                                if prev_inter.message.id != message.id:
                                    return
                                await prev_inter.response.defer()
                                nonlocal current_config_index
                                current_config_index = max(0, current_config_index - 1)
                                await show_config(current_config_index, prev_inter)               
                            prev_button.callback = prev_callback
                            
                            next_button = disnake.ui.Button(
                                style=disnake.ButtonStyle.secondary,
                                label="Следующая ▶️",
                                custom_id="next_config",
                                disabled=config_index == total_configs - 1  
                            )   
                            async def next_callback(next_inter):
                                if next_inter.message.id != message.id:
                                    return
                                await next_inter.response.defer()
                                nonlocal current_config_index
                                current_config_index = min(total_configs - 1, current_config_index + 1)
                                await show_config(current_config_index, next_inter)                   
                            next_button.callback = next_callback
                            
                            back_button = disnake.ui.Button(
                                style=disnake.ButtonStyle.secondary,
                                label="◀️ К моделям",
                                custom_id="back_to_models"
                            )                   
                            async def back_callback(back_inter):
                                if back_inter.message.id != message.id:
                                    return
                                await back_inter.response.defer()
                                await update_model_page(current_model_page)                  
                            back_button.callback = back_callback
                            
                            back_to_brands = disnake.ui.Button(
                                style=disnake.ButtonStyle.secondary,
                                label="🏠 К списку марок",
                                custom_id="back_to_brands"
                            )            
                            async def brands_callback(brands_inter):
                                if brands_inter.message.id != message.id:
                                    return
                                await brands_inter.response.defer()
                                await update_brand_page(current_brand_page)
                            
                            back_to_brands.callback = brands_callback


                            buy_button = disnake.ui.Button(
                                style=disnake.ButtonStyle.green,
                                label="🛒 Купить",
                                custom_id="buy_car"
                            )

                            async def buy_callback(buy_inter):
                                if buy_inter.message.id != message.id:
                                    return
                                await buy_inter.response.defer(ephemeral=True)
                                
                                try:
                                    has_space, total_slots, used_slots = await check_garage_space(inter.author.id)
                
                                    if not has_space:
                                        embed = disnake.Embed(
                                            title="❌ Недостаточно гаражных мест",
                                            description=(
                                                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                                f"🚗 **Занято мест:** {used_slots}/{total_slots}\n"
                                                f"❗ **Для покупки нового автомобиля необходимо:**\n"
                                                f"   • Купить дополнительное место (/купить_гараж)\n"
                                                f"   • Приобрести недвижимость с гаражом (/недвижимость)\n"
                                                f"   • Продать один из имеющихся автомобилей\n\n"
                                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                                            ),
                                            color=disnake.Color.red()
                                        )
                                        return await buy_inter.edit_original_response(embed=embed)
                                        
                                    addtoserver = await carmanager(inter.author.display_name, "добавить", f"{brand} {model}")
                                    if addtoserver == False:
                                        error_embed = disnake.Embed(
                                            title="❌ Ошибка",
                                            description=(
                                                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                                "🚫 Не удалось добавить автомобиль на сервер\n"
                                                "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                                            ),
                                            color=disnake.Color.red()
                                        )
                                        await buy_inter.edit_original_response(embed=error_embed)
                                        return
                                        
                                    # Check if user has enough money
                                    bal = unbclient.get_user_bal(1341469479510474813, int(buy_inter.author.id))
                                    if bal['cash'] < config[2]:
                                        await buy_inter.edit_original_response(embed=disnake.Embed(
                                            title="❌ Недостаточно средств",
                                            description=f"У вас недостаточно средств для покупки.\nНеобходимо: {config[2]:,}₽\nУ вас: {bal['cash']:,}₽",
                                            color=disnake.Color.red()
                                        ))
                                        return
                                        
                                    new_bal = bal['cash'] - config[2]
                                    unbclient.set_user_bal(1341469479510474813, int(buy_inter.author.id), cash=new_bal)
                                    
                                    cursor.execute('''INSERT INTO purchased_cars 
                                                 (brand, model, config, purchase_price, buyer_id, purchase_date)
                                                 VALUES (?, ?, ?, ?, ?, ?)''',
                                                 (brand, model, config[0], config[2],
                                                  buy_inter.author.id, datetime.now().isoformat()))
                                    conn.commit()
                                    
                                    success_embed = disnake.Embed(
                                        title="✅ Покупка успешна!",
                                        description=(
                                            "🎉 **Поздравляем с приобретением автомобиля!**\n\n"
                                            "━━━━━━━━━━ Информация о ТС ━━━━━━━━━━\n\n"
                                            f"🚗 **Марка:** {brand}\n"
                                            f"📋 **Модель:** {model}\n"
                                            f"⚙️ **Комплектация:** {config[0]}\n"
                                            f"📅 **Год выпуска:** {config[1]}\n"
                                            f"💰 **Стоимость:** {config[2]:,}₽\n"
                                            f"🏗️ **Тип кузова:** {config[3]}\n" 
                                            f"🔄 **Трансмиссия:** {config[4]}\n"
                                            f"🔧 **Двигатель:** {config[5]}\n\n"
                                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                            f"🔑 **ID автомобиля:** `{cursor.lastrowid}`"
                                        ),
                                        color=disnake.Color.green()
                                    )
                                    # Add vehicle image if available
                                    if config[6]:
                                        success_embed.set_image(url=config[6])
                                        
                                    # Remove previous buttons by sending an empty view
                                    await interaction.edit_original_response(view=None)
                                    await buy_inter.edit_original_response(embed=success_embed)
                                    
                                    # Send successful purchase log to bot's log channel
                                    logs_channel = bot.get_channel(1351455653197123665)
                                    purchase_log_embed = disnake.Embed(
                                        title="🛒 Покупка автомобиля",
                                        description=(
                                            "━━━━━━━━━━ Информация о покупке ━━━━━━━━━━\n\n"
                                            f"🚗 **Автомобиль:** {brand} {model} {config[0]}\n"
                                            f"👤 **Покупатель:** {buy_inter.author.mention}\n"
                                            f"💰 **Стоимость:** {config[2]:,}₽\n"
                                            f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                                        ),
                                        color=disnake.Color.green()
                                    )
                                    if config[6]:  # If car has image
                                        purchase_log_embed.set_image(url=config[6])
                                    await logs_channel.send(embed=purchase_log_embed)
                                    
                                except Exception as e:
                                    await buy_inter.edit_original_response(embed=disnake.Embed(
                                        title="❌ Ошибка",
                                        description=f"Произошла ошибка при покупке: {str(e)}",
                                        color=disnake.Color.red()
                                    ))

                            buy_button.callback = buy_callback
                            
                            # Добавляем все кнопки в правильном порядке
                            view.add_item(prev_button)
                            view.add_item(next_button)
                            view.add_item(buy_button)
                            view.add_item(back_button)
                            view.add_item(back_to_brands)
                            
                            # Отправляем сообщение с информацией об автомобиле
                            await interaction.edit_original_response(embed=embed, view=view)

                        # Показываем первую конфигурацию
                        await show_config(current_config_index, inter)

                    model_select.callback = model_callback
                    
                    view = disnake.ui.View(timeout=180)
                    view.add_item(model_select)
                    

                    if total_model_pages > 1:
                        prev_button = disnake.ui.Button(
                            style=disnake.ButtonStyle.secondary,
                            label="◀️ Предыдущая страница",
                            custom_id="prev_model_page",
                            disabled=page_num == 0
                        )
                        
                        next_button = disnake.ui.Button(
                            style=disnake.ButtonStyle.secondary,
                            label="Следующая страница ▶️",
                            custom_id="next_model_page",
                            disabled=page_num == total_model_pages - 1
                        )
                        
                        async def prev_page_callback(interaction):
                            if interaction.message.id != message.id:
                                return
                            await interaction.response.defer()
                            nonlocal current_model_page
                            current_model_page = max(0, current_model_page - 1)
                            await update_model_page(current_model_page)
                        
                        async def next_page_callback(interaction):
                            if interaction.message.id != message.id:
                                return
                            await interaction.response.defer()
                            nonlocal current_model_page
                            current_model_page = min(total_model_pages - 1, current_model_page + 1)
                            await update_model_page(current_model_page)
                        
                        prev_button.callback = prev_page_callback
                        next_button.callback = next_page_callback
                        
                        view.add_item(prev_button)
                        view.add_item(next_button)
                    

                    back_to_brands = disnake.ui.Button(
                        style=disnake.ButtonStyle.secondary,
                        label="🏠 К списку марок",
                        custom_id="back_to_brands"
                    )
                    
                    async def brands_callback(brands_inter):
                        if brands_inter.message.id != message.id:
                            return
                        await brands_inter.response.defer()
                        await update_brand_page(current_brand_page)
                    
                    back_to_brands.callback = brands_callback
                    view.add_item(back_to_brands)
                    
                    embed = disnake.Embed(
                        title=f"🚗 {brand}",
                        description=(
                            "━━━━━━━━━━ Выбор модели ━━━━━━━━━━\n\n"
                            "🚘 Пожалуйста, выберите модель автомобиля из списка ниже\n"
                            "✨ Каждая модель имеет уникальные характеристики и комплектации\n\n"
                            f"📄 Страница {page_num+1} из {total_model_pages}\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.green()
                    )
                    await interaction.edit_original_response(embed=embed, view=view)
                

                await update_model_page(current_model_page)
            
            select.callback = brand_callback
            
            view = disnake.ui.View(timeout=180)
            view.add_item(select)
            

            if total_brand_pages > 1:
                prev_button = disnake.ui.Button(
                    style=disnake.ButtonStyle.secondary,
                    label="◀️ Предыдущая страница",
                    custom_id="prev_brand_page",
                    disabled=page_num == 0
                )
                
                next_button = disnake.ui.Button(
                    style=disnake.ButtonStyle.secondary,
                    label="Следующая страница ▶️",
                    custom_id="next_brand_page",
                    disabled=page_num == total_brand_pages - 1
                )
                
                async def prev_page_callback(interaction):
                    if interaction.message.id != message.id:
                        return
                    await interaction.response.defer()
                    nonlocal current_brand_page
                    current_brand_page = max(0, current_brand_page - 1)
                    await update_brand_page(current_brand_page)
                
                async def next_page_callback(interaction):
                    if interaction.message.id != message.id:
                        return
                    await interaction.response.defer()
                    nonlocal current_brand_page
                    current_brand_page = min(total_brand_pages - 1, current_brand_page + 1)
                    await update_brand_page(current_brand_page)
                
                prev_button.callback = prev_page_callback
                next_button.callback = next_page_callback
                
                view.add_item(prev_button)
                view.add_item(next_button)
            
            embed = disnake.Embed(
                title="🏎️ Добро пожаловать в автосалон MaxiCars",
                description=(
                    "━━━━━━━━━━ Выбор автомобиля ━━━━━━━━━━\n\n"
                    "🚗 Пожалуйста, выберите марку автомобиля из списка ниже\n"
                    "💫 У нас представлены лучшие модели от ведущих производителей\n\n"
                    f"📄 Страница {page_num+1} из {total_brand_pages}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.blue()
            )
            await inter.edit_original_response(embed=embed, view=view)
        

        await update_brand_page(current_brand_page)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при загрузке автосалона: {str(e)}",
            color=disnake.Color.red()
        )
        if not inter.response.is_done():
            await inter.response.send_message(embed=error_embed)
        else:
            await inter.edit_original_response(embed=error_embed)



@garage_commands.sub_command(name="мои_авто", description="Показать все ваши автомобили")
async def my_cars(inter: ApplicationCommandInteraction):
    """Показывает все автомобили пользователя"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Get all cars owned by the user
        cursor.execute('''
            SELECT id, brand, model, config, purchase_date 
            FROM purchased_cars 
            WHERE buyer_id = ?
            ORDER BY purchase_date DESC
        ''', (inter.author.id,))
        cars = cursor.fetchall()

        # Get rented cars
        cursor.execute('''
            SELECT rc.car_id, pc.brand, pc.model, pc.config, rc.start_time, rc.end_time
            FROM rentcar rc
            JOIN purchased_cars pc ON rc.car_id = pc.id
            WHERE rc.renter_id = ? AND rc.status = 'active'
            AND rc.end_time > ?
        ''', (inter.author.id, datetime.now().isoformat()))
        rented_cars = cursor.fetchall()

        if not cars and not rented_cars:
            embed = disnake.Embed(
                title="🚗 Мой гараж",
                description="У вас пока нет автомобилей",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        # Create embed for owned cars
        for i, car in enumerate(cars):
            car_id, brand, model, config, purchase_date = car
            
            # Get car image from available_cars table
            cursor.execute('''
                SELECT image_data 
                FROM available_cars 
                WHERE brand = ? AND model = ? AND config = ?
            ''', (brand, model, config))
            car_image = cursor.fetchone()

            # Get full car details from available_cars table
            cursor.execute('''
                SELECT body_type, transmission, engine, year, price
                FROM available_cars 
                WHERE brand = ? AND model = ? AND config = ?
            ''', (brand, model, config))
            car_details = cursor.fetchone()

            if car_details:
                body_type, transmission, engine, year, price = car_details
                # Check if car is being rented out
                cursor.execute('''
                    SELECT renter_id, end_time 
                    FROM rentcar 
                    WHERE car_id = ? AND status = 'active' AND end_time > ?
                ''', (car_id, datetime.now().isoformat()))
                rental_info = cursor.fetchone()

                # Check if user is renting this car
                cursor.execute('''
                    SELECT owner_id, end_time 
                    FROM rentcar 
                    WHERE car_id = ? AND renter_id = ? AND status = 'active' AND end_time > ?
                ''', (car_id, inter.author.id, datetime.now().isoformat()))
                renting_info = cursor.fetchone()

                rental_status = ""
                if rental_info:
                    renter = await bot.fetch_user(rental_info[0])
                    rental_status = f"\n👥 **В аренде у:** {renter.mention}\n⏰ **До:** {datetime.fromisoformat(rental_info[1]).strftime('%d.%m.%Y %H:%M')}"
                elif renting_info:
                    owner = await bot.fetch_user(renting_info[0])
                    rental_status = f"\n👤 **Арендовано у:** {owner.mention}\n⏰ **До:** {datetime.fromisoformat(renting_info[1]).strftime('%d.%m.%Y %H:%M')}"

                embed = disnake.Embed(
                    title=f"🚗 {brand} {model} {config}",
                    description=(
                        "**━━━━━━━━━━** Информация об автомобиле **━━━━━━━━━━**\n\n"
                        f"🔑 **ID:** {car_id}\n"
                        f"📅 **Дата покупки:** {datetime.fromisoformat(purchase_date).strftime('%d.%m.%Y')}\n"
                        f"🏗️ **Тип кузова:** {body_type}\n"
                        f"🔄 **Трансмиссия:** {transmission}\n"
                        f"🔧 **Двигатель:** {engine}\n"
                        f"📅 **Год выпуска:** {year}\n"
                        f"💰 **Стоимость:** {price:,}₽"
                        f"{rental_status}\n\n"
                        "**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**"
                    ),
                    color=disnake.Color.gold()
                )
                if car_image and car_image[0]:
                    embed.set_thumbnail(url=car_image[0])
            else:
                embed = disnake.Embed(
                    title=f"🚗 {brand} {model} {config}",
                    description=(
                        "━━━━━━━━━━ Информация об автомобиле ━━━━━━━━━━\n\n"
                        f"🔑 **ID:** {car_id}\n"
                        f"📅 **Дата покупки:** {datetime.fromisoformat(purchase_date).strftime('%d.%m.%Y')}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.brand_green()
                )
                if car_image and car_image[0]:
                    embed.set_thumbnail(url=car_image[0])
            
            if i == 0:
                await inter.edit_original_response(embed=embed)
            else:
                await inter.followup.send(embed=embed, ephemeral=True)

        # Create embed for rented cars
        for rented_car in rented_cars:
            car_id, brand, model, config, start_time, end_time = rented_car
            
            cursor.execute('''
                SELECT image_data, body_type, transmission, engine, year, price
                FROM available_cars 
                WHERE brand = ? AND model = ? AND config = ?
            ''', (brand, model, config))
            car_details = cursor.fetchone()

            if car_details:
                image_url, body_type, transmission, engine, year, price = car_details
                embed = disnake.Embed(
                    title=f"🚗 {brand} {model} {config} (Арендован)",
                    description=(
                        "**━━━━━━━━━━** Информация об арендованном авто **━━━━━━━━━━**\n\n"
                        f"🔑 **ID:** {car_id}\n"
                        f"📅 **Начало аренды:** {datetime.fromisoformat(start_time).strftime('%d.%m.%Y %H:%M')}\n"
                        f"⏰ **Конец аренды:** {datetime.fromisoformat(end_time).strftime('%d.%m.%Y %H:%M')}\n"
                        f"🏗️ **Тип кузова:** {body_type}\n"
                        f"🔄 **Трансмиссия:** {transmission}\n"
                        f"🔧 **Двигатель:** {engine}\n"
                        f"📅 **Год выпуска:** {year}\n\n"
                        "**━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━**"
                    ),
                    color=disnake.Color.blue()
                )
                if image_url:
                    embed.set_thumbnail(url=image_url)
                await inter.followup.send(embed=embed, ephemeral=True)

        # Send summary message
        total_cars = len(cars) + len(rented_cars)
        summary = disnake.Embed(
            title="📋 Сводка",
            description=(
                f"Всего автомобилей в гараже: {total_cars}\n"
                f"• Собственных: {len(cars)}\n"
                f"• Арендованных: {len(rented_cars)}"
            ),
            color=disnake.Color.green()
        )
        await inter.followup.send(embed=summary, ephemeral=True)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении списка автомобилей: {str(e)}",
            color=disnake.Color.red()
        )
        if not inter.response.is_done():
            await inter.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await inter.followup.send(embed=error_embed, ephemeral=True)

@garage_commands.sub_command(name="инфо", description="Показать информацию о конкретном автомобиле")
async def car_info(inter: ApplicationCommandInteraction, car_id: int):
    """Показывает детальную информацию об автомобиле по ID"""
    try:
        await inter.response.defer()
        
        # Get car details from purchased_cars table
        cursor.execute('''
            SELECT brand, model, config, purchase_price, buyer_id, purchase_date
            FROM purchased_cars 
            WHERE id = ?
        ''', (car_id,))
        car = cursor.fetchone()

        if not car:
            embed = disnake.Embed(
                title="❌ Автомобиль не найден",
                description="Автомобиль с указанным ID не существует",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        brand, model, config, price, owner_id, purchase_date = car

        # Get additional car details from available_cars
        cursor.execute('''
            SELECT body_type, transmission, engine, year, image_data
            FROM available_cars 
            WHERE brand = ? AND model = ? AND config = ?
        ''', (brand, model, config))
        car_details = cursor.fetchone()

        if car_details:
            body_type, transmission, engine, year, image_url = car_details
            owner = await bot.fetch_user(owner_id)

            # Check if car is being rented
            cursor.execute('''
                SELECT renter_id, end_time 
                FROM rentcar 
                WHERE car_id = ? AND status = 'active' AND end_time > ?
            ''', (car_id, datetime.now().isoformat()))
            rental_info = cursor.fetchone()

            rental_status = ""
            if rental_info:
                renter = await bot.fetch_user(rental_info[0])
                rental_status = f"\n👥 **В аренде у:** {renter.mention}\n⏰ **До:** {datetime.fromisoformat(rental_info[1]).strftime('%d.%m.%Y %H:%M')}"

            embed = disnake.Embed(
                title=f"🚗 {brand} {model} {config}",
                description=(
                    "━━━━━━━━━━ Информация об автомобиле ━━━━━━━━━━\n\n"
                    f"👤 **Владелец:** {owner.mention}\n"
                    f"🔑 **ID автомобиля:** {car_id}\n"
                    f"📅 **Год выпуска:** {year}\n"
                    f"🏗️ **Тип кузова:** {body_type}\n"
                    f"🔄 **Трансмиссия:** {transmission}\n"
                    f"🔧 **Двигатель:** {engine}\n"
                    f"💰 **Стоимость:** {price:,}₽\n"
                    f"📅 **Дата покупки:** {datetime.fromisoformat(purchase_date).strftime('%d.%m.%Y')}"
                    f"{rental_status}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.blue()
            )

            if image_url:
                embed.set_image(url=image_url)

            embed.set_footer(text="База данных транспортных средств")
            embed.timestamp = datetime.now()

            await inter.edit_original_response(embed=embed)
        else:
            embed = disnake.Embed(
                title="⚠️ Ограниченная информация",
                description="Полная информация об автомобиле недоступна",
                color=disnake.Color.orange()
            )
            await inter.edit_original_response(embed=embed)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении информации: {str(e)}",
            color=disnake.Color.red()
        )
        if not inter.response.is_done():
            await inter.response.send_message(embed=error_embed)
        else:
            await inter.edit_original_response(embed=error_embed)

@garage_commands.sub_command(name="аренда", description="Сдать автомобиль в аренду другому игроку")
async def rent_car(
    inter: ApplicationCommandInteraction, 
    car_id: int, 
    арендатор: disnake.Member, 
    цена_в_час: int, 
    часов: int
):
    """Сдать автомобиль в аренду другому игроку"""
    try:
        await inter.response.defer()
        
        # Check if car exists and belongs to owner
        cursor.execute('''
            SELECT pc.*, ac.image_data
            FROM purchased_cars pc
            LEFT JOIN available_cars ac ON pc.brand = ac.brand 
                AND pc.model = ac.model AND pc.config = ac.config
            WHERE pc.id = ? AND pc.buyer_id = ?
        ''', (car_id, inter.author.id))
        car = cursor.fetchone()

        if not car:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Автомобиль с указанным ID не найден или вам не принадлежит",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
            
        # Check if car is already being rented
        cursor.execute('''
            SELECT * FROM rentcar 
            WHERE car_id = ? AND status = 'active' AND end_time > ?
        ''', (car_id, datetime.now().isoformat()))
        
        active_rental = cursor.fetchone()
        if active_rental:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Этот автомобиль уже находится в аренде",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
            
        total_price = цена_в_час * часов

        # Create rental offer embed
        embed = disnake.Embed(
            title="🚗 Предложение аренды автомобиля",
            description=(
                "━━━━━━━━━━ Информация об аренде ━━━━━━━━━━\n\n"
                f"🚘 **Автомобиль:** {car[1]} {car[2]} {car[3]}\n"
                f"⏰ **Срок аренды:** {часов} час(ов)\n"
                f"💰 **Стоимость в час:** {цена_в_час:,}₽\n"
                f"💵 **Итоговая стоимость:** {total_price:,}₽\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.blue()
        )

        if car[7]:  # If car has image
            embed.set_image(url=car[7])

        # Create buttons view
        view = disnake.ui.View(timeout=300)  # 5 minutes timeout

        accept_button = disnake.ui.Button(
            label="✅ Принять",
            style=disnake.ButtonStyle.green,
            custom_id="accept"
        )

        decline_button = disnake.ui.Button(
            label="❌ Отклонить",
            style=disnake.ButtonStyle.red,
            custom_id="decline"
        )

        async def accept_callback(interaction: disnake.MessageInteraction):
            if interaction.author != арендатор:
                return await interaction.response.send_message("Это предложение не для вас!", ephemeral=True)

            await interaction.response.defer()

            try:
                addtoserverpo = await carmanager(interaction.author.display_name, "добавить", f'{car[1]} {car[2]}')
                if addtoserverpo == False:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=(
                                        "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                        "🚫 Не удалось добавить автомобиль на сервер\n"
                                        "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.red()
                    )
                    await inter.followup.send(embed=error_embed)
                    
                addtoserverpr = await carmanager(inter.author.display_name, "удалить", f'{car[1]} {car[2]}')
                if addtoserverpr == False:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=(
                                        "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                        "🚫 Не удалось удалить автомобиль с сервера\n"
                                        "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.red()
                    )
                    await inter.followup.send(embed=error_embed)
                    
                # Check renter's balance
                bal = unbclient.get_user_bal(1341469479510474813, арендатор.id)
                if bal['cash'] < total_price:
                    return await interaction.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Недостаточно средств",
                            description=f"Необходимо: {total_price:,}₽\nУ вас: {bal['cash']:,}₽",
                            color=disnake.Color.red()
                        )
                    )
                    
                cursor.execute('''
                    INSERT INTO rentcar (
                        car_id, owner_id, renter_id, 
                        start_time, end_time, price_per_hour, total_price, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                ''', (
                    car_id, inter.author.id, арендатор.id,
                    datetime.now(), 
                    datetime.now() + timedelta(hours=часов),
                    цена_в_час, total_price
                ))
                conn.commit()

                # Transfer money
                new_renter_bal = bal['cash'] - total_price
                unbclient.set_user_bal(1341469479510474813, арендатор.id, cash=new_renter_bal)

                owner_bal = unbclient.get_user_bal(1341469479510474813, inter.author.id)
                new_owner_bal = owner_bal['cash'] + total_price
                unbclient.set_user_bal(1341469479510474813, inter.author.id, cash=new_owner_bal)

                success_embed = disnake.Embed(
                    title="✅ Аренда оформлена",
                    description=(
                        "━━━━━━━━━━ Информация об аренде ━━━━━━━━━━\n\n"
                        f"🚗 **Автомобиль:** {car[1]} {car[2]} {car[3]}\n"
                        f"👤 **Владелец:** {inter.author.mention}\n"
                        f"👥 **Арендатор:** {арендатор.mention}\n"
                        f"⏰ **Срок аренды:** {часов} час(ов)\n"
                        f"💰 **Оплачено:** {total_price:,}₽\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.green()
                )

                if car[7]:
                    success_embed.set_image(url=car[7])

                await interaction.edit_original_response(embed=success_embed, view=None)

                # Log the rental
                logs_channel = bot.get_channel(1351455653197123665)
                logs_embed = disnake.Embed(
                    title="🚗 Аренда автомобиля",
                    description=(
                        "━━━━━━━━━━ Информация об аренде ━━━━━━━━━━\n\n"
                        f"🚘 **Автомобиль:** {car[1]} {car[2]} {car[3]} (ID: {car_id})\n"
                        f"👤 **Владелец:** {inter.author.mention}\n"
                        f"👥 **Арендатор:** {арендатор.mention}\n"
                        f"⏰ **Срок:** {часов} час(ов)\n"
                        f"💰 **Сумма:** {total_price:,}₽\n"
                        f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.green()
                )
                if car[7]:
                    logs_embed.set_image(url=car[7])
                await logs_channel.send(embed=logs_embed)

            except Exception as e:
                await interaction.edit_original_response(
                    embed=disnake.Embed(
                        title="❌ Ошибка",
                        description=str(e),
                        color=disnake.Color.red()
                    )
                )

        async def decline_callback(interaction: disnake.MessageInteraction):
            if interaction.author != арендатор:
                return await interaction.response.send_message("Это предложение не для вас!", ephemeral=True)

            await interaction.response.defer()

            decline_embed = disnake.Embed(
                title="❌ Аренда отклонена",
                description=(
                    f"**Владелец:** {inter.author.mention}\n"
                    f"**Арендатор:** {арендатор.mention}\n"
                    f"**Автомобиль:** {car[1]} {car[2]} {car[3]}\n"
                    "**Причина:** Арендатор отклонил предложение"
                ),
                color=disnake.Color.red()
            )

            await interaction.edit_original_response(embed=decline_embed, view=None)

        accept_button.callback = accept_callback
        decline_button.callback = decline_callback

        view.add_item(accept_button)
        view.add_item(decline_button)

        await inter.edit_original_response(embed=embed, view=view)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при создании предложения аренды: {str(e)}",
            color=disnake.Color.red()
        )
        if not inter.response.is_done():
            await inter.response.send_message(embed=error_embed)
        else:
            await inter.edit_original_response(embed=error_embed)

@garage_commands.sub_command(name="продать", description="Продать автомобиль другому игроку")
async def sell_car(
    inter: ApplicationCommandInteraction, 
    car_id: int, 
    покупатель: disnake.Member, 
    цена: int
):
    """Продать автомобиль другому игроку"""
    try:    
        await inter.response.defer()
        if цена < 1:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Цена продажи должна быть больше 0",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
            
        has_space, total_slots, used_slots = await check_garage_space(покупатель.id)
        
        if not has_space:
            embed = disnake.Embed(
                title="❌ Недостаточно гаражных мест у покупателя",
                description=(
                    "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                    f"👤 **Покупатель:** {покупатель.mention}\n"
                    f"🚗 **Занято мест:** {used_slots}/{total_slots}\n"
                    f"❗ **У покупателя нет свободных гаражных мест**\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        # Check if car exists and belongs to seller
        cursor.execute('''
            SELECT pc.brand, pc.model, pc.config, pc.buyer_id, ac.body_type, 
                   ac.transmission, ac.engine, ac.year, ac.image_data
            FROM purchased_cars pc
            LEFT JOIN available_cars ac ON pc.brand = ac.brand 
                AND pc.model = ac.model AND pc.config = ac.config
            WHERE pc.id = ?
        ''', (car_id,))
        car = cursor.fetchone()

        if not car:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Автомобиль с указанным ID не найден",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
            
        # Check if car is being rented
        cursor.execute('''
            SELECT * FROM rentcar 
            WHERE car_id = ? AND status = 'active' AND end_time > ?
        ''', (car_id, datetime.now().isoformat()))
        
        rental = cursor.fetchone()
        if rental:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Этот автомобиль находится в аренде и не может быть продан\nДождитесь срока окончания аренды!",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        brand, model, config, owner_id, body_type, transmission, engine, year, image_url = car

        if owner_id != inter.author.id:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Этот автомобиль вам не принадлежит",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        # Create sale embed
        embed = disnake.Embed(
            title="🚗 Предложение о покупке автомобиля",
            color=disnake.Color.blue()
        )

        # Add vehicle information
        embed.add_field(
            name="📋 Информация об автомобиле",
            value=(
                f"**Марка:** {brand}\n"
                f"**Модель:** {model}\n"
                f"**Комплектация:** {config}\n"
                f"**Год выпуска:** {year}\n"
                f"**Тип кузова:** {body_type}\n"
                f"**Трансмиссия:** {transmission}\n"
                f"**Двигатель:** {engine}\n"
                f"**ID автомобиля:** {car_id}"
            ),
            inline=False
        )

        # Add sale information
        embed.add_field(
            name="💰 Информация о сделке",
            value=(
                f"**Продавец:** {inter.author.mention}\n"
                f"**Покупатель:** {покупатель.mention}\n"
                f"**Цена:** {цена:,}₽"
            ),
            inline=False
        )

        if image_url:
            embed.set_image(url=image_url)

        embed.set_footer(text="Нажмите на кнопку ниже, чтобы принять или отклонить предложение")
        embed.timestamp = datetime.now()


        view = disnake.ui.View(timeout=300)  

        # Create accept button
        accept_button = disnake.ui.Button(
            label="✅ Принять",
            style=disnake.ButtonStyle.green,
            custom_id="accept"
        )

        # Create decline button
        decline_button = disnake.ui.Button(
            label="❌ Отклонить", 
            style=disnake.ButtonStyle.red,
            custom_id="decline"
        )

        async def accept_callback(interaction: disnake.MessageInteraction):
            if interaction.author != покупатель:
                return await interaction.response.send_message("Это предложение не для вас!", ephemeral=True)

            await interaction.response.defer()

            await interaction.edit_original_response(
                embed=disnake.Embed(
                    title="⏳ Обработка покупки",
                    description="Пожалуйста, подождите...",
                    color=disnake.Color.yellow()
                ),
                view=None
            )

            try:
                # Check buyer's balance
                bal = unbclient.get_user_bal(1341469479510474813, покупатель.id)
                if bal['cash'] < цена:
                    return await interaction.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Недостаточно средств",
                            description="У вас недостаточно средств для покупки!",
                            color=disnake.Color.red()
                        )
                    )
                addtoserverpr = await carmanager(inter.author.display_name, "удалить", f'{brand} {model}')
                if addtoserverpr == False:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=(
                                        "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                        "🚫 Не удалось удалить автомобиль с сервера\n"
                                        "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.red()
                    )
                    await inter.followup.send(embed=error_embed)
                addtoserverpo = await carmanager(interaction.author.display_name, "добавить", f'{brand} {model}')
                if addtoserverpo == False:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=(
                                        "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                        "🚫 Не удалось добавить автомобиль на сервер\n"
                                        "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.red()
                    )
                    await inter.followup.send(embed=error_embed)        

                # Update car ownership
                cursor.execute('''
                    UPDATE purchased_cars 
                    SET buyer_id = ?, purchase_date = ?
                    WHERE id = ?
                ''', (покупатель.id, datetime.now().isoformat(), car_id))

                # Transfer money
                new_buyer_bal = bal['cash'] - цена
                unbclient.set_user_bal(1341469479510474813, покупатель.id, cash=new_buyer_bal)

                seller_bal = unbclient.get_user_bal(1341469479510474813, inter.author.id)
                new_seller_bal = seller_bal['cash'] + цена
                unbclient.set_user_bal(1341469479510474813, inter.author.id, cash=new_seller_bal)

                conn.commit()

                success_embed = disnake.Embed(
                    title="✅ Сделка успешно завершена",
                    color=disnake.Color.green()
                )

                success_embed.add_field(
                    name="📋 Информация об автомобиле",
                    value=(
                        "━━━━━━━━━━ Детали автомобиля ━━━━━━━━━━\n\n"
                        f"🚗 **Марка:** {brand}\n"
                        f"📝 **Модель:** {model}\n" 
                        f"⚙️ **Комплектация:** {config}\n"
                        f"📅 **Год выпуска:** {year}\n"
                        f"🔑 **ID автомобиля:** {car_id}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    inline=False
                )

                success_embed.add_field(
                    name="💰 Информация о сделке",
                    value=(
                        "━━━━━━━━━━ Детали сделки ━━━━━━━━━━\n\n"
                        f"💎 **Продавец:** {inter.author.mention}\n"
                        f"🛒 **Покупатель:** {покупатель.mention}\n"
                        f"💵 **Сумма сделки:** {цена:,}₽\n"
                        f"⏰ **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    inline=False
                )

                if image_url:
                    success_embed.set_image(url=image_url)

                # Remove buttons by sending None as view
                await interaction.edit_original_response(embed=success_embed, view=None)
                
                logs_channel = bot.get_channel(1351455653197123665)
                logs_embed = disnake.Embed(
                    title="🔄 Продажа автомобиля",
                    description=(
                        "━━━━━━━━━━ Информация о сделке ━━━━━━━━━━\n\n"
                        f"🚗 **Автомобиль:** {brand} {model} {config}\n"
                        f"🔑 **ID:** {car_id}\n"
                        f"💎 **Продавец:** {inter.author.mention}\n"
                        f"🛒 **Покупатель:** {покупатель.mention}\n"
                        f"💰 **Сумма:** {цена:,}₽\n"
                        f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.green()
                )
                if image_url:
                    logs_embed.set_image(url=image_url)
                await logs_channel.send(embed=logs_embed)
            except Exception as e:
                await interaction.edit_original_response(
                    embed=disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Произошла ошибка: {str(e)}",
                        color=disnake.Color.red()
                    )
                )

        async def decline_callback(interaction: disnake.MessageInteraction):
            if interaction.author != покупатель:
                return await interaction.response.send_message("Это предложение не для вас!", ephemeral=True)

            await interaction.response.defer()

            decline_embed = disnake.Embed(
                title="❌ Сделка отменена",
                description=(
                    f"**Продавец:** {inter.author.mention}\n"
                    f"**Покупатель:** {покупатель.mention}\n"
                    f"**Автомобиль:** {brand} {model} {config}\n"
                    f"**Причина:** Покупатель отклонил предложение"
                ),
                color=disnake.Color.red()
            )

            # Remove buttons by sending None as view
            await interaction.edit_original_response(embed=decline_embed, view=None)

        # Set button callbacks
        accept_button.callback = accept_callback
        decline_button.callback = decline_callback

        # Add buttons to view
        view.add_item(accept_button)
        view.add_item(decline_button)

        # Send the sale offer
        await inter.edit_original_response(embed=embed, view=view)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при создании предложения: {str(e)}",
            color=disnake.Color.red()
        )
        if not inter.response.is_done():
            await inter.response.send_message(embed=error_embed)
        else:
            await inter.edit_original_response(embed=error_embed)

@garage_commands.sub_command(name="продать_гос", description="Продать автомобиль государству за 75% стоимости")
async def sell_car_to_state(inter: ApplicationCommandInteraction, car_id: int):
    """Продать автомобиль государству за 75% стоимости"""
    try:
        await inter.response.defer()
        
        # Check if car exists and belongs to seller
        cursor.execute('''
            SELECT pc.*, ac.price
            FROM purchased_cars pc
            LEFT JOIN available_cars ac ON pc.brand = ac.brand 
                AND pc.model = ac.model AND pc.config = ac.config
            WHERE pc.id = ? AND pc.buyer_id = ?
        ''', (car_id, inter.author.id))
        car = cursor.fetchone()

        if not car:
            embed = disnake.Embed(
                title="❌ Ошибка", 
                description="Автомобиль с указанным ID не найден или вам не принадлежит",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
            
        # Check if car is being rented
        cursor.execute('''
            SELECT * FROM rentcar 
            WHERE car_id = ? AND status = 'active' AND end_time > ?
        ''', (car_id, datetime.now().isoformat()))
        
        rental = cursor.fetchone()
        if rental:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Этот автомобиль находится в аренде и не может быть продан\nДождитесь срока окончания аренды!",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        refund_amount = int(car[4] * 0.75)  # car[7] is the price from available_cars
        confirm_embed = disnake.Embed(
            title="⚠️ Подтверждение продажи",
            description=(
                "━━━━━━━━━━ Информация о продаже ━━━━━━━━━━\n\n"
                f"🚗 **Автомобиль:** {car[1]} {car[2]} {car[3]}\n"
                f"💰 **Сумма возврата:** {refund_amount:,}₽ (75% от стоимости)\n"
                "⚠️ **Это действие необратимо!**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.yellow()
        )

        # Create confirmation buttons
        view = disnake.ui.View(timeout=60)  # 60 seconds timeout
        
        async def confirm_callback(interaction):
            if interaction.user.id != inter.author.id:
                return await interaction.response.send_message("Это не ваша продажа!", ephemeral=True)
            addtoserverpr = await carmanager(inter.author.display_name, "удалить", f'{car[1]} {car[2]}')
            if addtoserverpr == False:
                error_embed = disnake.Embed(
                    title="❌ Ошибка",
                    description=(
                                        "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                        "🚫 Не удалось удалить автомобиль с сервера\n"
                                        "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.red()
                )
                await inter.followup.send(embed=error_embed)

            # Update user's balance
            bal = unbclient.get_user_bal(1341469479510474813, inter.author.id)
            new_bal = bal['cash'] + refund_amount
            unbclient.set_user_bal(1341469479510474813, inter.author.id, cash=new_bal)

            # Delete car from database
            cursor.execute('DELETE FROM purchased_cars WHERE id = ?', (car_id,))
            conn.commit()
            success_embed = disnake.Embed(
                title="✅ Автомобиль продан государству",
                description=(
                    "━━━━━━━━━━ Информация о продаже ━━━━━━━━━━\n\n"
                    f"🚗 **Автомобиль:** {car[1]} {car[2]} {car[3]}\n"
                    f"💰 **Получено:** {refund_amount:,}₽ (75% от стоимости)\n"
                    f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.green()
            )
            await interaction.response.edit_message(embed=success_embed, view=None)
            # Log the transaction
            logs_channel = bot.get_channel(1351455653197123665)
            logs_embed = disnake.Embed(
                title="🏢 Продажа автомобиля государству",
                description=(
                    "━━━━━━━━━━ Информация о сделке ━━━━━━━━━━\n\n"
                    f"🚗 **Автомобиль:** {car[1]} {car[2]} {car[3]}\n"
                    f"👤 **Продавец:** {inter.author.mention}\n"
                    f"💰 **Сумма возврата:** {refund_amount:,}₽\n"
                    f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.blue()
            )
            await logs_channel.send(embed=logs_embed)

        async def cancel_callback(interaction):
            if interaction.user.id != inter.author.id:
                return await interaction.response.send_message("Это не ваша продажа!", ephemeral=True)
            
            cancel_embed = disnake.Embed(
                title="❌ Продажа отменена",
                description="Вы отменили продажу автомобиля государству",
                color=disnake.Color.red()
            )
            await interaction.response.edit_message(embed=cancel_embed, view=None)

        # Add buttons to view
        confirm_button = disnake.ui.Button(label="✅ Подтвердить", style=disnake.ButtonStyle.green)
        cancel_button = disnake.ui.Button(label="❌ Отменить", style=disnake.ButtonStyle.red)
        
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        # Send confirmation message
        await inter.edit_original_response(embed=confirm_embed, view=view)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при продаже автомобиля: {str(e)}",
            color=disnake.Color.red()
        )
        if not inter.response.is_done():
            await inter.response.send_message(embed=error_embed)
        else:
            await inter.edit_original_response(embed=error_embed)

async def check_property_purchase_restrictions(user_id, property_type):
    try:
        cursor.execute('''
            SELECT property_type FROM real_estate 
            WHERE buyer_id = ?
        ''', (user_id,))
        owned_property_types = [row[0] for row in cursor.fetchall()]
        if property_type == "Гараж":
            if not any(p_type in ["Дом", "Квартира"] for p_type in owned_property_types):
                return False, "Для покупки гаража необходимо сначала приобрести дом или квартиру"
            elif "Гараж" in owned_property_types:
                return False, "У вас уже есть гараж. Вы можете владеть только одним гаражом"
        elif property_type == "Квартира" and "Квартира" in owned_property_types:
            return False, "У вас уже есть квартира. Вы можете владеть только одной квартирой"
        elif property_type == "Дом" and "Дом" in owned_property_types:
            return False, "У вас уже есть дом. Вы можете владеть только одним домом"
        return True, None
    except Exception as e:
        print(f"Error checking property restrictions: {e}")
        return False, f"Произошла ошибка при проверке ограничений: {str(e)}"

@bot.command()
async def недвижимость(ctx):
    """Shows available real estate properties"""
    try:
        initial_embed = disnake.Embed(
            title="⌛ Загрузка базы недвижимости...",
            description="Пожалуйста, подождите...",
            color=disnake.Color.blue()
        )
        message = await ctx.send(embed=initial_embed)

        # Get all property types
        cursor.execute('SELECT DISTINCT property_type FROM real_estate WHERE buyer_id IS NULL')
        property_types = [row[0] for row in cursor.fetchall()]

        if not property_types:
            embed = disnake.Embed(
                title="🏠 База недвижимости",
                description="В данный момент нет доступной недвижимости",
                color=disnake.Color.red()
            )
            return await message.edit(embed=embed)

        # Create property type selection menu
        type_select = disnake.ui.Select(
            placeholder="Выберите тип недвижимости",
            options=[disnake.SelectOption(label=prop_type) for prop_type in property_types]
        )

        async def type_callback(interaction):
            if interaction.message.id != message.id:
                return
            
            await interaction.response.defer()
            prop_type = type_select.values[0]

            # Get classes for selected property type
            cursor.execute('SELECT DISTINCT class FROM real_estate WHERE property_type = ? AND buyer_id IS NULL', (prop_type,))
            classes = [row[0] for row in cursor.fetchall()]

            class_select = disnake.ui.Select(
                placeholder="Выберите класс недвижимости",
                options=[disnake.SelectOption(label=class_) for class_ in classes]
            )

            async def class_callback(inter):
                if inter.message.id != message.id:
                    return
                
                await inter.response.defer()
                selected_class = class_select.values[0]

                # Get properties of selected type and class
                cursor.execute('''
                    SELECT * FROM real_estate 
                    WHERE property_type = ? AND class = ? AND buyer_id IS NULL
                    ORDER BY price
                ''', (prop_type, selected_class))
                properties = cursor.fetchall()

                current_index = 0
                total_properties = len(properties)

                async def show_property(index, interaction):
                    property = properties[index]
                    embed = disnake.Embed(
                        title=f"🏠 {property[5]} класса {property[4]}",
                        description=(
                            "━━━━━━━━━━ Информация о недвижимости ━━━━━━━━━━\n\n"
                            f"📍 **Адрес:** {property[2]}\n"
                            f"💰 **Стоимость:** {property[3]:,}₽\n"
                            f"📏 **Площадь:** {property[7]} м²\n"
                            f"🚗 **Парковочных мест:** {property[6]}\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.gold()
                    )

                    if property[8]:  # house photo
                        embed.set_image(url=property[8])
                    if property[9]:  # location photo
                        embed.set_thumbnail(url=property[9])

                    embed.set_footer(text=f"Объект {index + 1} из {total_properties}")

                    view = disnake.ui.View(timeout=180)

                    # Navigation buttons
                    prev_button = disnake.ui.Button(
                        style=disnake.ButtonStyle.secondary,
                        label="◀️ Предыдущий",
                        disabled=index == 0
                    )
                    next_button = disnake.ui.Button(
                        style=disnake.ButtonStyle.secondary,
                        label="Следующий ▶️",
                        disabled=index == total_properties - 1
                    )
                     # Check if user can buy this property type
                    can_purchase, error_message = await check_property_purchase_restrictions(
                        interaction.author.id, property[5]
                    )
                    
                    buy_button = disnake.ui.Button(
                        style=disnake.ButtonStyle.green,
                        label="🛒 Купить",
                        disabled=not can_purchase
                    )
                    
                    # Add tooltip to embed if button is disabled
                    if not can_purchase and error_message:
                        embed.add_field(
                            name="⚠️ Ограничение покупки",
                            value=error_message,
                            inline=False
                        )
                    back_button = disnake.ui.Button(
                        style=disnake.ButtonStyle.secondary,
                        label="🔙 Назад"
                    )

                    async def prev_callback(b_inter):
                        nonlocal current_index
                        current_index = max(0, current_index - 1)
                        await b_inter.response.defer()
                        await show_property(current_index, b_inter)

                    async def next_callback(b_inter):
                        nonlocal current_index
                        current_index = min(total_properties - 1, current_index + 1)
                        await b_inter.response.defer() 
                        await show_property(current_index, b_inter)

                    async def buy_callback(b_inter):
                        await b_inter.response.defer(ephemeral=True)
                        
                        try:
                            # Check user's balance
                            bal = unbclient.get_user_bal(1341469479510474813, int(b_inter.author.id))
                            if bal['cash'] < property[3]:
                                await b_inter.edit_original_response(
                                    embed=disnake.Embed(
                                        title="❌ Недостаточно средств",
                                        description=f"Необходимо: {property[3]:,}₽\nУ вас: {bal['cash']:,}₽",
                                        color=disnake.Color.red()
                                    )
                                )
                                return

                            # Update property ownership
                            cursor.execute('''
                                UPDATE real_estate 
                                SET buyer_id = ? 
                                WHERE id = ?
                            ''', (b_inter.author.id, property[0]))

                            # Update user's balance
                            new_bal = bal['cash'] - property[3]
                            unbclient.set_user_bal(1341469479510474813, int(b_inter.author.id), cash=new_bal)
                            
                            conn.commit()

                            success_embed = disnake.Embed(
                                title="✅ Поздравляем с покупкой!",
                                description=(
                                    "━━━━━━━━━━ Информация о покупке ━━━━━━━━━━\n\n"
                                    f"🏠 **Тип:** {property[5]}\n"
                                    f"🌟 **Класс:** {property[4]}\n"
                                    f"📍 **Адрес:** {property[2]}\n"
                                    f"💰 **Стоимость:** {property[3]:,}₽\n"
                                    f"📏 **Площадь:** {property[7]} м²\n"
                                    f"🚗 **Парковочных мест:** {property[6]}\n\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                                ),
                                color=disnake.Color.green()
                            )
                            
                            if property[8]:
                                success_embed.set_image(url=property[8])

                            await b_inter.edit_original_response(embed=success_embed)
                            await interaction.message.edit(view=None)

                            logs_channel = bot.get_channel(1351455653197123665)
                            purchase_log_embed = disnake.Embed(
                                title="🏠 Покупка недвижимости",
                                description=(
                                    "━━━━━━━━━━ Информация о покупке ━━━━━━━━━━\n\n"
                                    f"🏘️ **Объект:** {property[5]} класса {property[4]}\n"
                                    f"👤 **Покупатель:** {b_inter.author.mention}\n"
                                    f"📍 **Адрес:** {property[2]}\n"
                                    f"💰 **Стоимость:** {property[3]:,}₽\n"
                                    f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                                ),
                                color=disnake.Color.green()
                            )
                            await logs_channel.send(embed=purchase_log_embed)
                        except Exception as e:
                            await b_inter.edit_original_response(
                                embed=disnake.Embed(
                                    title="❌ Ошибка",
                                    description=str(e),
                                    color=disnake.Color.red()
                                )
                            )

                    async def back_callback(b_inter):
                        embed = disnake.Embed(
                            title="🏠 Выбор класса недвижимости",
                            description=(
                                "━━━━━━━━━━ Выбор класса ━━━━━━━━━━\n\n"
                                "🏘️ Пожалуйста, выберите класс недвижимости\n"
                                "✨ Каждый класс имеет свои уникальные характеристики\n\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ),
                            color=disnake.Color.blue()
                        )
                        view = disnake.ui.View(timeout=180)
                        view.add_item(class_select)
                        view.add_item(back_to_types)
                        await b_inter.response.edit_message(embed=embed, view=view)

                    prev_button.callback = prev_callback
                    next_button.callback = next_callback
                    buy_button.callback = buy_callback
                    back_button.callback = back_callback

                    view.add_item(prev_button)
                    view.add_item(next_button)
                    view.add_item(buy_button)
                    view.add_item(back_button)

                    await interaction.edit_original_response(embed=embed, view=view)

                back_to_types = disnake.ui.Button(
                    style=disnake.ButtonStyle.secondary,
                    label="🏠 К списку типов"
                )

                async def back_to_types_callback(b_inter):
                    embed = disnake.Embed(
                        title="🏠 База недвижимости",
                        description=(
                            "━━━━━━━━━━ Выбор типа недвижимости ━━━━━━━━━━\n\n"
                            "🏘️ Пожалуйста, выберите тип недвижимости\n"
                            "✨ У нас представлены различные варианты для любого бюджета\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.blue()
                    )
                    view = disnake.ui.View(timeout=180)
                    view.add_item(type_select)
                    await b_inter.response.edit_message(embed=embed, view=view)

                back_to_types.callback = back_to_types_callback

                await show_property(current_index, inter)

            class_select.callback = class_callback

            embed = disnake.Embed(
                title="🏠 Выбор класса недвижимости",
                description=(
                    "━━━━━━━━━━ Выбор класса ━━━━━━━━━━\n\n"
                    "🏘️ Пожалуйста, выберите класс недвижимости\n"
                    "✨ Каждый класс имеет свои уникальные характеристики\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.blue()
            )
            view = disnake.ui.View(timeout=180)
            view.add_item(class_select)
            await interaction.edit_original_response(embed=embed, view=view)

        type_select.callback = type_callback

        embed = disnake.Embed(
            title="🏠 База недвижимости",
            description=(
                "━━━━━━━━━━ Выбор типа недвижимости ━━━━━━━━━━\n\n"
                "🏘️ Пожалуйста, выберите тип недвижимости\n"
                "✨ У нас представлены различные варианты для любого бюджета\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.blue()
        )
        view = disnake.ui.View(timeout=180)
        view.add_item(type_select)
        await message.edit(embed=embed, view=view)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)

@bot.slash_command(
    name="недвижимость",
    description="Команды для управления недвижимостью",
    guild_ids=[1341469479510474813]
)
async def real_estate(inter: disnake.ApplicationCommandInteraction):
    """Group command for real estate management"""
    pass

@real_estate.sub_command(
    name="моя",
    description="Показать вашу недвижимость"
)
async def my_property(inter: disnake.ApplicationCommandInteraction):
    """Shows all real estate owned by the user with pagination"""
    try:
        await inter.response.defer()
        
        # Get all properties owned by the user
        cursor.execute('''
            SELECT * FROM real_estate 
            WHERE buyer_id = ?
            ORDER BY property_type, class
        ''', (inter.author.id,))
        properties = cursor.fetchall()

        if not properties:
            embed = disnake.Embed(
                title="🏠 Моя недвижимость",
                description="У вас пока нет недвижимости",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        current_page = 0
        total_pages = len(properties)

        async def show_property(page_num, interaction=None):
            property = properties[page_num]
            embed = disnake.Embed(
                title=f"🏠 {property[5]} класса {property[4]}",
                description=(
                    "━━━━━━━━━━ Информация о недвижимости ━━━━━━━━━━\n\n"
                    f"🔑 **ID:** {property[0]}\n"
                    f"📍 **Адрес:** {property[2]}\n"
                    f"💰 **Стоимость:** {property[3]:,}₽\n"
                    f"📏 **Площадь:** {property[7]} м²\n"
                    f"🚗 **Парковочных мест:** {property[6]}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.gold()
            )

            if property[8]:  # house photo
                embed.set_image(url=property[8])
            if property[9]:  # location photo
                embed.set_thumbnail(url=property[9])

            embed.set_footer(text=f"Страница {page_num + 1} из {total_pages}")
            embed.timestamp = datetime.now()

            # Create navigation buttons
            view = disnake.ui.View(timeout=180)

            prev_button = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label="◀️ Предыдущий",
                disabled=page_num == 0
            )
            next_button = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label="Следующий ▶️",
                disabled=page_num == total_pages - 1
            )

            # Add upgrade button for garage
            if property[5] == "Гараж":
                cursor.execute('SELECT slots FROM garage_slots WHERE id = ?', (property[0],))
                garage_result = cursor.fetchone()
                current_slots = garage_result[0] if garage_result else 0

                if current_slots < 4:  
                    upgrade_button = disnake.ui.Button(
                        style=disnake.ButtonStyle.green,
                        label="⬆️ Улучшить гараж",
                        custom_id="upgrade_garage"
                    )

                    async def upgrade_callback(b_inter):
                        if b_inter.user.id != inter.author.id:
                            return await b_inter.response.send_message("Это не ваш гараж!", ephemeral=True)

                        await b_inter.response.defer()

                        try:
                            cost = 0
                            new_slots = 0
                            if current_slots == 1:
                                new_slots = 2
                                cost = 700000
                            elif current_slots == 2:
                                new_slots = 4
                                cost = 2500000

                            bal = unbclient.get_user_bal(1341469479510474813, inter.author.id)
                            if bal['cash'] < cost:
                                return await b_inter.followup.send(
                                    f"Недостаточно средств! Требуется: {cost:,}₽", 
                                    ephemeral=True
                                )

                            if garage_result:
                                cursor.execute(
                                    'UPDATE real_estate SET garage_slots = ? WHERE id = ?',
                                    (new_slots, property[0])
                                )

                            new_bal = bal['cash'] - cost
                            unbclient.set_user_bal(1341469479510474813, inter.author.id, cash=new_bal)


                            if new_slots == 4:
                                cursor.execute(
                                    'INSERT INTO medals (user_id, medal_type, award_date) VALUES (?, "Гармония Пространства", ?)',
                                    (inter.author.id, datetime.now().isoformat())
                                )


                                guild = b_inter.guild
                                role = disnake.utils.get(guild.roles, name='Медаль "Гармония Пространства"')
                                if role:
                                    await b_inter.author.add_roles(role)
                                    

                                    medal_embed = disnake.Embed(
                                        title="🏅 Получена медаль!",
                                        description=(
                                            "Поздравляем! Вы получили:\n"
                                            "**Медаль «Гармония Пространства»**\n"
                                            "За максимальное улучшение гаража"
                                        ),
                                        color=disnake.Color.gold()
                                    )
                                    await b_inter.author.send(embed=medal_embed)

                            conn.commit()


                            success_embed = disnake.Embed(
                                title="✅ Гараж улучшен!",
                                description=(
                                    f"Уровень гаража повышен!\n"
                                    f"Новое количество слотов: {new_slots}\n"
                                    f"Потрачено: {cost:,}₽"
                                ),
                                color=disnake.Color.green()
                            )
                            await b_inter.followup.send(embed=success_embed)
                            await show_property(page_num, b_inter)

                        except Exception as e:
                            await b_inter.followup.send(f"Ошибка: {str(e)}", ephemeral=True)

                    upgrade_button.callback = upgrade_callback
                    view.add_item(upgrade_button)

            async def prev_callback(b_inter):
                nonlocal current_page
                if b_inter.user.id != inter.author.id:
                    return await b_inter.response.send_message("Это не ваш список!", ephemeral=True)
                current_page = max(0, current_page - 1)
                await b_inter.response.defer()
                await show_property(current_page, b_inter)

            async def next_callback(b_inter):
                nonlocal current_page
                if b_inter.user.id != inter.author.id:
                    return await b_inter.response.send_message("Это не ваш список!", ephemeral=True)
                current_page = min(total_pages - 1, current_page + 1)
                await b_inter.response.defer()
                await show_property(current_page, b_inter)

            prev_button.callback = prev_callback
            next_button.callback = next_callback

            view.add_item(prev_button)
            view.add_item(next_button)

            if interaction:
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await inter.edit_original_response(embed=embed, view=view)

        await show_property(current_page)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении списка недвижимости: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@real_estate.sub_command(
    name="игрока",
    description="Показать недвижимость другого игрока"
)
@commands.has_any_role('Смотрящий за RolePlay','Модератор', 'ГИБДД', 'Администратор')
async def player_property(
    inter: disnake.ApplicationCommandInteraction,
    игрок: disnake.Member = commands.Param(description="Игрок, чью недвижимость нужно показать")
):
    """Shows all real estate owned by the specified player"""
    try:
        await inter.response.defer()
        
        # Get all properties owned by the specified user
        cursor.execute('''
            SELECT * FROM real_estate 
            WHERE buyer_id = ?
            ORDER BY property_type, class
        ''', (игрок.id,))
        properties = cursor.fetchall()

        if not properties:
            embed = disnake.Embed(
                title="🏠 Недвижимость игрока",
                description=f"У {игрок.mention} нет недвижимости",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        # Create embed for each property
        for property in properties:
            embed = disnake.Embed(
                title=f"🏠 {property[5]} класса {property[4]}",
                description=(
                    f"👤 **Владелец:** {игрок.mention}\n"
                    f"🔑 **ID:** {property[0]}\n"
                    f"📍 **Адрес:** {property[2]}\n"
                    f"💰 **Стоимость:** {property[3]:,}₽\n"
                    f"📏 **Площадь:** {property[7]} м²\n"
                    f"🚗 **Парковочных мест:** {property[6]}\n\n"
                ),
                color=disnake.Color.gold()
            )

            # Add property photos if available
            if property[8]:  # house photo
                embed.set_image(url=property[8])
            if property[9]:  # location photo
                embed.set_thumbnail(url=property[9])

            embed.timestamp = datetime.now()
            await inter.followup.send(embed=embed)

        # Send summary message
        summary = disnake.Embed(
            title="📋 Сводка",
            description=f"Всего объектов недвижимости у {игрок.display_name}: {len(properties)}",
            color=disnake.Color.green()
        )
        await inter.followup.send(embed=summary)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении списка недвижимости: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@real_estate.sub_command(
    name="объект",
    description="Показать информацию о конкретном объекте недвижимости"
)
async def property_info(
    inter: disnake.ApplicationCommandInteraction,
    id: int = commands.Param(description="ID объекта недвижимости")
):
    """Shows detailed information about a specific property by ID"""
    try:
        await inter.response.defer()
        
        # Get property details from database
        cursor.execute('SELECT * FROM real_estate WHERE id = ?', (id,))
        property = cursor.fetchone()

        if not property:
            embed = disnake.Embed(
                title="❌ Объект не найден",
                description="Объект недвижимости с указанным ID не существует",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        # Create embed with property information
        embed = disnake.Embed(
            title=f"🏠 {property[5]} класса {property[4]}",
            description=(
                f"🔑 **ID:** {property[0]}\n"
                f"📍 **Адрес:** {property[2]}\n"
                f"💰 **Стоимость:** {property[3]:,}₽\n"
                f"📏 **Площадь:** {property[7]} м²\n"
                f"🚗 **Парковочных мест:** {property[6]}\n"
            ),
            color=disnake.Color.blue()
        )

        # Add owner information if property is owned
        if property[1]:  # buyer_id
            owner = await bot.fetch_user(property[1])
            embed.add_field(
                name="👤 Владелец",
                value=f"{owner.mention}",
                inline=False
            )

        # Add photos if available
        if property[8]:  # house photo
            embed.set_image(url=property[8])
        if property[9]:  # location photo
            embed.set_thumbnail(url=property[9])

        embed.set_footer(text="База данных недвижимости")
        embed.timestamp = datetime.now()

        await inter.edit_original_response(embed=embed)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении информации: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@real_estate.sub_command(
    name="продать_игроку",
    description="Продать недвижимость другому игроку"
)
async def sell_to_player(
    inter: disnake.ApplicationCommandInteraction,
    id: int = commands.Param(description="ID объекта недвижимости"),
    покупатель: disnake.Member = commands.Param(description="Игрок, которому продаётся недвижимость"),
    цена: int = commands.Param(description="Цена продажи")
):
    """Command to sell a property to another player"""
    try:
        await inter.response.defer()
        
        # Check if property exists and belongs to seller
        cursor.execute('''
            SELECT * FROM real_estate 
            WHERE id = ? AND buyer_id = ?
        ''', (id, inter.author.id))
        property = cursor.fetchone()
        
        if цена < 1:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Цена продажи должна быть больше 0",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
            
        if not property:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Объект недвижимости с указанным ID не найден или вам не принадлежит",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        # Create sale embed
        embed = disnake.Embed(
            title="🏠 Предложение о покупке недвижимости",
            color=disnake.Color.blue()
        )

        # Add property information
        embed.add_field(
            name="📋 Информация об объекте",
            value=(
                f"**Тип:** {property[5]}\n"
                f"**Класс:** {property[4]}\n"
                f"**Адрес:** {property[2]}\n"
                f"**Площадь:** {property[7]} м²\n"
                f"**Парковочных мест:** {property[6]}\n"
                f"**ID объекта:** {property[0]}"
            ),
            inline=False
        )

        # Add sale information
        embed.add_field(
            name="💰 Информация о сделке",
            value=(
                f"**Продавец:** {inter.author.mention}\n"
                f"**Покупатель:** {покупатель.mention}\n"
                f"**Цена:** {цена:,}₽"
            ),
            inline=False
        )

        if property[8]:  # house photo
            embed.set_image(url=property[8])
        if property[9]:  # location photo
            embed.set_thumbnail(url=property[9])

        embed.set_footer(text="Нажмите на кнопку ниже, чтобы принять или отклонить предложение")
        embed.timestamp = datetime.now()

        # Create buttons view
        view = disnake.ui.View(timeout=300)  # 5 minutes timeout

        # Create accept button
        accept_button = disnake.ui.Button(
            label="✅ Принять",
            style=disnake.ButtonStyle.green,
            custom_id="accept"
        )

        # Create decline button
        decline_button = disnake.ui.Button(
            label="❌ Отклонить",
            style=disnake.ButtonStyle.red,
            custom_id="decline"
        )

        async def accept_callback(interaction: disnake.MessageInteraction):
            if interaction.author != покупатель:
                return await interaction.response.send_message("Это предложение не для вас!", ephemeral=True)

            await interaction.response.defer()

            try:
                # Check buyer's balance
                bal = unbclient.get_user_bal(1341469479510474813, покупатель.id)
                if bal['cash'] < цена:
                    return await interaction.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Недостаточно средств",
                            description=f"Необходимо: {цена:,}₽\nУ вас: {bal['cash']:,}₽",
                            color=disnake.Color.red()
                        )
                    )

                # Update property ownership
                cursor.execute('''
                    UPDATE real_estate 
                    SET buyer_id = ? 
                    WHERE id = ?
                ''', (покупатель.id, id))

                # Transfer money
                new_buyer_bal = bal['cash'] - цена
                unbclient.set_user_bal(1341469479510474813, покупатель.id, cash=new_buyer_bal)

                seller_bal = unbclient.get_user_bal(1341469479510474813, inter.author.id)
                new_seller_bal = seller_bal['cash'] + цена
                unbclient.set_user_bal(1341469479510474813, inter.author.id, cash=new_seller_bal)

                conn.commit()

                success_embed = disnake.Embed(
                    title="✅ Сделка успешно завершена",
                    description=(
                        "━━━━━━━━━━ Информация о сделке ━━━━━━━━━━\n\n"
                        f"🏠 **Объект:** {property[5]} класса {property[4]}\n"
                        f"📍 **Адрес:** {property[2]}\n"
                        f"💰 **Сумма сделки:** {цена:,}₽\n"
                        f"👤 **Продавец:** {inter.author.mention}\n"
                        f"🛒 **Покупатель:** {покупатель.mention}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.green()
                )

                if property[8]:
                    success_embed.set_image(url=property[8])

                await interaction.edit_original_response(embed=success_embed, view=None)

                # Log the transaction
                logs_channel = bot.get_channel(1351455653197123665)
                logs_embed = disnake.Embed(
                    title="🏠 Продажа недвижимости",
                    description=(
                        "━━━━━━━━━━ Информация о сделке ━━━━━━━━━━\n\n"
                        f"🏘️ **Объект:** {property[5]} класса {property[4]}\n"
                        f"📍 **Адрес:** {property[2]}\n"
                        f"💰 **Сумма:** {цена:,}₽\n"
                        f"👤 **Продавец:** {inter.author.mention}\n"
                        f"🛒 **Покупатель:** {покупатель.mention}\n"
                        f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.green()
                )
                if property[8]:
                    logs_embed.set_image(url=property[8])
                await logs_channel.send(embed=logs_embed)

            except Exception as e:
                await interaction.edit_original_response(
                    embed=disnake.Embed(
                        title="❌ Ошибка",
                        description=str(e),
                        color=disnake.Color.red()
                    )
                )

        async def decline_callback(interaction: disnake.MessageInteraction):
            if interaction.author != покупатель:
                return await interaction.response.send_message("Это предложение не для вас!", ephemeral=True)

            await interaction.response.defer()

            decline_embed = disnake.Embed(
                title="❌ Сделка отменена",
                description=(
                    f"**Продавец:** {inter.author.mention}\n"
                    f"**Покупатель:** {покупатель.mention}\n"
                    f"**Объект:** {property[5]} класса {property[4]}\n"
                    f"**Причина:** Покупатель отклонил предложение"
                ),
                color=disnake.Color.red()
            )

            await interaction.edit_original_response(embed=decline_embed, view=None)

        # Set button callbacks
        accept_button.callback = accept_callback
        decline_button.callback = decline_callback

        # Add buttons to view
        view.add_item(accept_button)
        view.add_item(decline_button)

        # Send the sale offer
        await inter.edit_original_response(embed=embed, view=view)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при создании предложения: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@real_estate.sub_command(
    name="продать_государству",
    description="Продать недвижимость государству"
)
async def sell_to_state(
    inter: disnake.ApplicationCommandInteraction,
    id: int = commands.Param(description="ID объекта недвижимости")
):
    """Command to sell a property to the state (removes owner but keeps the record)"""
    try:
        await inter.response.defer()
        
        # Check if property exists and belongs to seller
        cursor.execute('''
            SELECT * FROM real_estate 
            WHERE id = ? AND buyer_id = ?
        ''', (id, inter.author.id))
        property = cursor.fetchone()

        if not property:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Объект недвижимости с указанным ID не найден или вам не принадлежит",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        # Calculate refund amount (75% of original price)
        refund_amount = int(property[3] * 0.75)  # property[3] is the price

        # Create confirmation embed
        confirm_embed = disnake.Embed(
            title="⚠️ Подтверждение продажи",
            description=(
                "━━━━━━━━━━ Информация о продаже ━━━━━━━━━━\n\n"
                f"🏠 **Объект:** {property[5]} класса {property[4]}\n"
                f"📍 **Адрес:** {property[2]}\n"
                f"💰 **Сумма возврата:** {refund_amount:,}₽ (75% от стоимости)\n"
                "⚠️ **Это действие необратимо!**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.yellow()
        )

        if property[8]:  # Add property photo if available
            confirm_embed.set_image(url=property[8])

        # Create confirmation buttons
        view = disnake.ui.View(timeout=60)  # 60 seconds timeout

        async def confirm_callback(interaction):
            if interaction.user.id != inter.author.id:
                return await interaction.response.send_message(
                    "Это не ваша продажа!", ephemeral=True
                )

            try:
                # Update user's balance
                bal = unbclient.get_user_bal(1341469479510474813, inter.author.id)
                new_bal = bal['cash'] + refund_amount
                unbclient.set_user_bal(1341469479510474813, inter.author.id, cash=new_bal)

                # Remove owner from property
                cursor.execute(
                    'UPDATE real_estate SET buyer_id = NULL WHERE id = ?', 
                    (id,)
                )
                conn.commit()

                success_embed = disnake.Embed(
                    title="✅ Объект продан государству",
                    description=(
                        "━━━━━━━━━━ Информация о продаже ━━━━━━━━━━\n\n"
                        f"🏠 **Объект:** {property[5]} класса {property[4]}\n"
                        f"📍 **Адрес:** {property[2]}\n"
                        f"💰 **Получено:** {refund_amount:,}₽\n"
                        f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.green()
                )

                if property[8]:
                    success_embed.set_image(url=property[8])

                await interaction.response.edit_message(embed=success_embed, view=None)

                # Log the transaction
                logs_channel = bot.get_channel(1351455653197123665)
                logs_embed = disnake.Embed(
                    title="🏢 Продажа недвижимости государству",
                    description=(
                        "━━━━━━━━━━ Информация о сделке ━━━━━━━━━━\n\n"
                        f"🏠 **Объект:** {property[5]} класса {property[4]}\n"
                        f"📍 **Адрес:** {property[2]}\n"
                        f"👤 **Продавец:** {inter.author.mention}\n"
                        f"💰 **Сумма возврата:** {refund_amount:,}₽\n"
                        f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.blue()
                )
                if property[8]:
                    logs_embed.set_image(url=property[8])
                await logs_channel.send(embed=logs_embed)

            except Exception as e:
                await interaction.response.send_message(
                    f"Произошла ошибка при продаже: {str(e)}", 
                    ephemeral=True
                )

        async def cancel_callback(interaction):
            if interaction.user.id != inter.author.id:
                return await interaction.response.send_message(
                    "Это не ваша продажа!", ephemeral=True
                )

            cancel_embed = disnake.Embed(
                title="❌ Продажа отменена",
                description="Вы отменили продажу недвижимости государству",
                color=disnake.Color.red()
            )
            await interaction.response.edit_message(embed=cancel_embed, view=None)

        # Add buttons to view
        confirm_button = disnake.ui.Button(
            label="✅ Подтвердить", 
            style=disnake.ButtonStyle.green
        )
        cancel_button = disnake.ui.Button(
            label="❌ Отменить", 
            style=disnake.ButtonStyle.red
        )

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        # Send confirmation message
        await inter.edit_original_response(embed=confirm_embed, view=view)

    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при продаже: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

async def check_garage_space(user_id):
    """
    Универсальная функция для проверки наличия свободных гаражных мест
    tuple: (bool, int, int) - (достаточно ли мест, всего мест, занято мест)
    """
    try:
        # Получаем количество автомобилей пользователя
        cursor.execute('SELECT COUNT(*) FROM purchased_cars WHERE buyer_id = ?', (user_id,))
        owned_cars = cursor.fetchone()[0] or 0
        
        # Получаем дополнительные гаражные места
        cursor.execute('SELECT slots FROM garage_slots WHERE owner_id = ?', (user_id,))
        garage_result = cursor.fetchone()
        additional_slots = garage_result[0] if garage_result else 0
        
        # Получаем места от недвижимости
        cursor.execute('SELECT SUM(garage_slots) FROM real_estate WHERE buyer_id = ?', (user_id,))
        estate_slots = cursor.fetchone()[0] or 0
        
        # Проверяем наличие активного бронирования отеля
        cursor.execute('''
            SELECT COUNT(*) FROM hotel_bookings
            WHERE user_id = ? AND end_date > ?
        ''', (user_id, datetime.now().isoformat()))
        has_hotel = cursor.fetchone()[0] > 0
        
        # Добавляем 1 место, если есть активное бронирование отеля
        hotel_slots = 1 if has_hotel else 0
        
        # Общее количество мест
        total_slots = additional_slots + estate_slots + hotel_slots
        
        # Проверяем, есть ли свободные места
        has_space = owned_cars < total_slots
        
        return (has_space, total_slots, owned_cars)
    except Exception as e:
        print(f"Ошибка при проверке гаражных мест: {e}")
        return (False, 0, 0)

@bot.command()
async def отель(ctx, days: int = None):
    """Command to rent a hotel room for a specified number of days"""
    try:
        # Fixed hotel price
        price_per_day = 10000
        hotel_name = "Гранд Отель"
        hotel_description = "Комфортабельный отель в центре города с видом на парк"
        hotel_location = "ул. Центральная, 15"
        hotel_image = "https://cdn.discordapp.com/attachments/1344985538670759996/1361428256506773534/22.png?ex=67ff611e&is=67fe0f9e&hm=980a5ab500787e26e2554772f3107fb24f61b35cf1c091fa78b827610644c1c9&"  # Replace with actual image URL
        
        if days is None:
            # Show hotel information
            embed = disnake.Embed(
                title=f"🏨 {hotel_name}",
                description=(
                    "━━━━━━━━━━ Информация об отеле ━━━━━━━━━━\n\n"
                    f"📍 **Расположение:** {hotel_location}\n"
                    f"💰 **Стоимость:** {price_per_day:,}₽ в сутки\n\n"
                    f"📝 **Описание:** {hotel_description}\n\n"
                    "Для бронирования используйте команду:\n"
                    "`!отель [количество_дней]`\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.blue()
            )
            
            if hotel_image:
                embed.set_image(url=hotel_image)
            
            await ctx.send(embed=embed)
            
        else:
            # Direct booking with specified days
            if days < 1 or days > 30:
                embed = disnake.Embed(
                    title="❌ Ошибка",
                    description="Количество дней должно быть от 1 до 30",
                    color=disnake.Color.red()
                )
                return await ctx.send(embed=embed)
            
            # Calculate total price
            total_price = price_per_day * days
            
            # Create confirmation view
            confirm_view = disnake.ui.View(timeout=60)
            
            confirm_button = disnake.ui.Button(
                style=disnake.ButtonStyle.green,
                label="✅ Подтвердить"
            )
            cancel_button = disnake.ui.Button(
                style=disnake.ButtonStyle.red,
                label="❌ Отменить"
            )
            
            async def confirm_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Это не ваша бронь!", ephemeral=True)
                
                await interaction.response.defer()
                
                try:
                    # Check user's balance
                    bal = unbclient.get_user_bal(1341469479510474813, ctx.author.id)
                    if bal['cash'] < total_price:
                        return await interaction.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Недостаточно средств",
                                description=f"Необходимо: {total_price:,}₽\nУ вас: {bal['cash']:,}₽",
                                color=disnake.Color.red()
                            ),
                            view=None
                        )
                    
                    # Calculate booking dates
                    start_date = datetime.now()
                    end_date = start_date + timedelta(days=days)
                    
                    # Deduct payment from user's balance
                    new_bal = bal['cash'] - total_price
                    unbclient.set_user_bal(1341469479510474813, ctx.author.id, cash=new_bal)
                    
                    # Record booking in database
                    cursor.execute('''
                        INSERT INTO hotel_bookings 
                        (user_id, start_date, end_date, days, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        ctx.author.id, start_date.isoformat(), 
                        end_date.isoformat(), days, total_price
                    ))
                    conn.commit()
                    
                    # Create success embed
                    success_embed = disnake.Embed(
                        title="✅ Бронирование успешно!",
                        description=(
                            "━━━━━━━━━━ Информация о бронировании ━━━━━━━━━━\n\n"
                            f"🏨 **Отель:** {hotel_name}\n"
                            f"📍 **Расположение:** {hotel_location}\n"
                            f"📅 **Период:** {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
                            f"⏱️ **Количество дней:** {days}\n"
                            f"💰 **Стоимость:** {total_price:,}₽\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.green()
                    )
                    
                    if hotel_image:
                        success_embed.set_image(url=hotel_image)
                    
                    await interaction.edit_original_response(embed=success_embed, view=None)
                    
                    # Log the booking
                    logs_channel = bot.get_channel(1351455653197123665)
                    log_embed = disnake.Embed(
                        title="🏨 Бронирование отеля",
                        description=(
                            f"👤 **Игрок:** {ctx.author.mention}\n"
                            f"🏨 **Отель:** {hotel_name}\n"
                            f"📅 **Период:** {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
                            f"⏱️ **Дней:** {days}\n"
                            f"💰 **Стоимость:** {total_price:,}₽\n"
                            f"📆 **Дата бронирования:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                        ),
                        color=disnake.Color.blue()
                    )
                    await logs_channel.send(embed=log_embed)
                    
                except Exception as e:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Произошла ошибка при бронировании: {str(e)}",
                        color=disnake.Color.red()
                    )
                    await interaction.edit_original_response(embed=error_embed, view=None)
            
            async def cancel_callback(interaction):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Это не ваша бронь!", ephemeral=True)
                
                cancel_embed = disnake.Embed(
                    title="❌ Бронирование отменено",
                    description="Вы отменили бронирование отеля",
                    color=disnake.Color.red()
                )
                await interaction.response.edit_message(embed=cancel_embed, view=None)
            
            confirm_button.callback = confirm_callback
            cancel_button.callback = cancel_callback
            
            confirm_view.add_item(confirm_button)
            confirm_view.add_item(cancel_button)
            
            # Create confirmation embed
            confirm_embed = disnake.Embed(
                title="🏨 Подтверждение бронирования",
                description=(
                    "━━━━━━━━━━ Детали бронирования ━━━━━━━━━━\n\n"
                    f"🏨 **Отель:** {hotel_name}\n"
                    f"📍 **Расположение:** {hotel_location}\n"
                    f"📅 **Период:** {days} дней\n"
                    f"💰 **Стоимость:** {price_per_day:,}₽ × {days} = {total_price:,}₽\n\n"
                    "Пожалуйста, подтвердите бронирование\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.gold()
            )
            
            if hotel_image:
                confirm_embed.set_image(url=hotel_image)
            
            await ctx.send(embed=confirm_embed, view=confirm_view)
    
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)

@bot.command()
async def мой_отель(ctx):
    """Shows current hotel booking for the user"""
    try:
        # Get active booking for the user
        cursor.execute('''
            SELECT * FROM hotel_bookings
            WHERE user_id = ? AND end_date > ?
        ''', (ctx.author.id, datetime.now().isoformat()))
        
        booking = cursor.fetchone()
        
        if not booking:
            embed = disnake.Embed(
                title="🏨 Мой отель",
                description="У вас нет активного бронирования отеля",
                color=disnake.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Create embed with booking information
        booking_id, user_id, start_date, end_date, days, total_price = booking
        
        start_date_dt = datetime.fromisoformat(start_date)
        end_date_dt = datetime.fromisoformat(end_date)
        
        # Calculate remaining time
        now = datetime.now()
        time_remaining = end_date_dt - now
        days_remaining = time_remaining.days
        hours_remaining = time_remaining.seconds // 3600
        
        embed = disnake.Embed(
            title="🏨 Мой отель",
            description=(
                "━━━━━━━━━━ Информация о проживании ━━━━━━━━━━\n\n"
                f"📅 **Период:** {start_date_dt.strftime('%d.%m.%Y')} - {end_date_dt.strftime('%d.%m.%Y')}\n"
                f"⏱️ **Забронировано дней:** {days}\n"
                f"⌛ **Осталось:** {days_remaining}д {hours_remaining}ч\n"
                f"💰 **Стоимость:** {total_price:,}₽\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.blue()
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении информации: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)
@tasks.loop(minutes=1)
async def check_hotel_bookings():
    try:
        # Get all active bookings that have expired
        cursor.execute('''
            SELECT * FROM hotel_bookings 
            WHERE end_date < ?
        ''', (datetime.now().isoformat(),))
        
        expired_bookings = cursor.fetchall()
        
        for booking in expired_bookings:
            booking_id, user_id, start_date, end_date, days, total_price = booking
            
            # Delete expired booking
            cursor.execute('DELETE FROM hotel_bookings WHERE id = ?', (booking_id,))
            conn.commit()
            
            # Notify user if needed
            try:
                user = await bot.fetch_user(user_id)
                if user:
                    embed = disnake.Embed(
                        title="🏨 Бронирование завершено",
                        description=(
                            "Ваше бронирование отеля завершено.\n"
                            f"Период: {datetime.fromisoformat(start_date).strftime('%d.%m.%Y')} - "
                            f"{datetime.fromisoformat(end_date).strftime('%d.%m.%Y')}"
                        ),
                        color=disnake.Color.blue()
                    )
                    await user.send(embed=embed)
            except Exception as e:
                print(f"Failed to notify user about hotel booking expiration: {e}")
                
    except Exception as e:
        print(f"Error in hotel booking check task: {e}")

@tasks.loop(minutes=30)
async def check_rentals():
    try:
        # Get all active rentals
        cursor.execute('''
            SELECT car_id, renter_id, end_time 
            FROM rentcar 
            WHERE status = 'active'
        ''')
        active_rentals = cursor.fetchall()
        
        current_time = datetime.now()
        
        for rental in active_rentals:
            car_id, renter_id, end_time = rental
            end_time = datetime.fromisoformat(end_time)
            
            if current_time > end_time:
                renter = await bot.fetch_user(renter_id)
                # Update rental status to expired
                cursor.execute('''
                    UPDATE rentcar 
                    SET status = 'expired' 
                    WHERE car_id = ? AND renter_id = ? AND status = 'active'
                ''', (car_id, renter_id))
                conn.commit()
                cursor.execute('''SELECT brand, model FROM purchased_cars WHERE id=?''',(car_id,))
                brandmodel = cursor.fetchone()
                addtoserverpr = await carmanager(renter.display_name, "удалить", f'{brandmodel[0]} {brandmodel[1]}')
                if addtoserverpr == False:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=(
                                        "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                        "🚫 Не удалось удалить автомобиль с сервера\n"
                                        "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.red()
                    )
                await ctx.send(embed=error_embed)
                # Notify users if needed
                try:
                    if renter:
                        embed = disnake.Embed(
                            title="🚗 Аренда завершена",
                            description=f"Срок аренды автомобиля (ID: {car_id}) истек",
                            color=disnake.Color.red()
                        )
                        await renter.send(embed=embed)
                except Exception as e:
                    print(f"Failed to notify user about rental expiration: {e}")
                    
    except Exception as e:
        print(f"Error in rental check task: {e}")

@tasks.loop(minutes=2)
async def check_server_status():
    """Check server player count and automatically enable/disable job system"""
    try:
        download_file_from_server()
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'latest_players.json')
                
        with open(file_path, 'r', encoding='utf-8') as f:
            player_data = json.load(f)
            
        if isinstance(player_data, dict) and "playerCount" in player_data and "players" in player_data:
            total_players = player_data["playerCount"]
            players_dict = player_data["players"]
            
            moderator_count = 0
            if isinstance(players_dict, dict):
                for player_key, player_info in players_dict.items():
                    player_name = player_info.get("name", "")
                    if player_name in BEAMMP_MODERATORS:
                        moderator_count += 1
            elif isinstance(players_dict, list):
                for player_info in players_dict:
                    if isinstance(player_info, dict) and "name" in player_info:
                        player_name = player_info["name"]
                        if player_name in BEAMMP_MODERATORS:
                            moderator_count += 1
        elif isinstance(player_data, list):
            total_players = len(player_data)
            moderator_count = 0
            
            for player in player_data:
                if isinstance(player, dict) and 'name' in player:
                    username = player['name']
                else:
                    username = str(player).strip()
                if username in BEAMMP_MODERATORS:
                    moderator_count += 1
        else:
            total_players = 0
            moderator_count = 0
        
        cursor.execute('SELECT jobs_enabled FROM jobs_settings WHERE id = 1')
        result = cursor.fetchone()
        current_status = result[0] if result else 0
            
        should_enable = total_players >= 4 and moderator_count >= 1
        
        if should_enable and not current_status:

            cursor.execute('UPDATE jobs_settings SET jobs_enabled = 1 WHERE id = 1')
            conn.commit()

            logs_channel = bot.get_channel(1351455653197123665)
            log_embed = disnake.Embed(
                title="🔧 Система работ",
                description=(
                    "📅 **Действие:** Система работ автоматически включена\n"
                    f"👥 **Игроков на сервере:** {total_players}\n"
                    f"👮 **Модераторов на сервере:** {moderator_count}"
                ),
                color=disnake.Color.blue()
            )
            await logs_channel.send(embed=log_embed)
            au_channel = bot.get_channel(1353803771565838438)
            au_embed = disnake.Embed(
                title="🔧 Система работ",
                description=(
                    "📅 **Действие:** Система работ автоматически включена\n"
                    f"👥 **Игроков на сервере:** {total_players}\n"
                    f"👮 **Модераторов на сервере:** {moderator_count}"
                ),
                color=disnake.Color.blue()
            )
            await au_channel.send(embed=au_embed)
                

        elif not should_enable and current_status:

            cursor.execute('''
                SELECT a.user_id, a.job_id, a.start_time, j.hourly_pay, j.name, uj.worked_hours
                FROM active_shifts a
                JOIN jobs j ON a.job_id = j.id
                JOIN user_jobs uj ON a.job_id = uj.job_id AND a.user_id = uj.user_id
            ''')
            active_shifts = cursor.fetchall()


            for shift in active_shifts:
                user_id, job_id, start_time, hourly_pay, job_name, previous_worked_hours = shift

                start_time_dt = datetime.fromisoformat(start_time)
                end_time_dt = datetime.now()
                time_worked = end_time_dt - start_time_dt
                hours_worked = time_worked.total_seconds() / 3600
                payment = int(hours_worked * hourly_pay)


                bal = unbclient.get_user_bal(1341469479510474813, user_id)
                new_bal = bal['cash'] + payment
                unbclient.set_user_bal(1341469479510474813, user_id, cash=new_bal)

                total_worked_hours = previous_worked_hours + hours_worked
                cursor.execute('''
                    UPDATE user_jobs 
                    SET worked_hours = ? 
                    WHERE user_id = ? AND job_id = ?
                ''', (total_worked_hours, user_id, job_id))

                try:
                    user = await bot.fetch_user(user_id)
                    if user:
                        shift_end_embed = disnake.Embed(
                            title="⚠️ Система работ отключена",
                            description=(
                                "━━━━━━━━━━ Окончание смены ━━━━━━━━━━\n\n"
                                f"💼 **Работа:** {job_name}\n"
                                f"⏰ **Отработано:** {hours_worked:.1f} ч\n"
                                f"💰 **Получено:** {payment:,}₽\n\n"
                                "Система работ автоматически отключена из-за недостатка игроков/модераторов\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ),
                            color=disnake.Color.yellow()
                        )
                        await user.send(embed=shift_end_embed)
                except Exception as e:
                    print(f"Failed to notify user {user_id}: {e}")


            cursor.execute('DELETE FROM active_shifts')
            

            cursor.execute('UPDATE jobs_settings SET jobs_enabled = 0 WHERE id = 1')
            conn.commit()
            

            logs_channel = bot.get_channel(1351455653197123665)
            log_embed = disnake.Embed(
                title="🔧 Система работ",
                description=(
                    "📅 **Действие:** Система работ автоматически выключена\n"
                    f"👥 **Игроков на сервере:** {total_players}\n"
                    f"👮 **Модераторов на сервере:** {moderator_count}\n"
                    f"📊 **Завершено смен:** {len(active_shifts)}"
                ),
                color=disnake.Color.red()
            )
            await logs_channel.send(embed=log_embed)
            au_channel = bot.get_channel(1353803771565838438)
            au_embed = disnake.Embed(
                title="🔧 Система работ",
                description=(
                    "📅 **Действие:** Система работ автоматически выключена\n"
                    f"👥 **Игроков на сервере:** {total_players}\n"
                    f"👮 **Модераторов на сервере:** {moderator_count}\n"
                    f"📊 **Завершено смен:** {len(active_shifts)}"
                ),
                color=disnake.Color.red()
            )
            await au_channel.send(embed=au_embed)
                
    except Exception as e:
        print(f"Error in server status check: {e}")


@bot.command()
@commands.has_any_role('Смотрящий за RolePlay',"Модератор", "Высшее руководство")
async def включить_работы(ctx):
    """Enables the job system on the server"""
    try:
        cursor.execute('UPDATE jobs_settings SET jobs_enabled = 1 WHERE id = 1')
        conn.commit()
        
        embed = disnake.Embed(
            title="✅ Система работ включена",
            description="Система работ успешно активирована на сервере",
            color=disnake.Color.green()
        )
        await ctx.send(embed=embed)
        
        # Log the action
        logs_channel = bot.get_channel(1351455653197123665)
        log_embed = disnake.Embed(
            title="🔧 Система работ",
            description=f"👤 **Администратор:** {ctx.author.mention}\n📅 **Действие:** Система работ включена",
            color=disnake.Color.blue()
        )
        await logs_channel.send(embed=log_embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при включении системы работ: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)

@bot.command()
@commands.has_any_role('Смотрящий за RolePlay',"Модератор", "Высшее руководство")
async def выключить_работы(ctx):
    """Disables the job system on the server and ends all active shifts"""
    try:
        # Get all active shifts before disabling the system
        cursor.execute('''
            SELECT a.user_id, a.job_id, a.start_time, j.hourly_pay, j.name, uj.worked_hours
            FROM active_shifts a
            JOIN jobs j ON a.job_id = j.id
            JOIN user_jobs uj ON a.job_id = uj.job_id AND a.user_id = uj.user_id
        ''')
        active_shifts = cursor.fetchall()

        # Process all active shifts
        for shift in active_shifts:
            user_id, job_id, start_time, hourly_pay, job_name, previous_worked_hours = shift
            
            # Calculate payment for each worker
            start_time_dt = datetime.fromisoformat(start_time)
            end_time_dt = datetime.now()
            time_worked = end_time_dt - start_time_dt
            hours_worked = time_worked.total_seconds() / 3600
            payment = int(hours_worked * hourly_pay)
            
            # Update user's balance
            bal = unbclient.get_user_bal(1341469479510474813, user_id)
            new_bal = bal['cash'] + payment
            unbclient.set_user_bal(1341469479510474813, user_id, cash=new_bal)
            
            # Update worked hours
            total_worked_hours = previous_worked_hours + hours_worked
            cursor.execute('''
                UPDATE user_jobs 
                SET worked_hours = ? 
                WHERE user_id = ? AND job_id = ?
            ''', (total_worked_hours, user_id, job_id))
            
            # Try to notify the user
            try:
                user = await bot.fetch_user(user_id)
                if user:
                    shift_end_embed = disnake.Embed(
                        title="⚠️ Система работ отключена",
                        description=(
                            "━━━━━━━━━━ Окончание смены ━━━━━━━━━━\n\n"
                            f"💼 **Работа:** {job_name}\n"
                            f"⏰ **Отработано:** {hours_worked:.1f} ч\n"
                            f"💰 **Получено:** {payment:,}₽\n\n"
                            "Система работ отключена администратором\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.yellow()
                    )
                    await user.send(embed=shift_end_embed)
            except Exception as e:
                print(f"Failed to notify user {user_id}: {e}")

        # Clear all active shifts
        cursor.execute('DELETE FROM active_shifts')
        
        # Disable the job system
        cursor.execute('UPDATE jobs_settings SET jobs_enabled = 0 WHERE id = 1')
        conn.commit()
        
        embed = disnake.Embed(
            title="🚫 Система работ выключена",
            description=(
                "Система работ успешно деактивирована на сервере\n"
                f"Завершено активных смен: {len(active_shifts)}"
            ),
            color=disnake.Color.red()
        )
        await ctx.send(embed=embed)
        
        # Log the action
        logs_channel = bot.get_channel(1351455653197123665)
        log_embed = disnake.Embed(
            title="🔧 Система работ",
            description=(
                f"👤 **Администратор:** {ctx.author.mention}\n"
                f"📅 **Действие:** Система работ выключена\n"
                f"📊 **Завершено смен:** {len(active_shifts)}"
            ),
            color=disnake.Color.blue()
        )
        await logs_channel.send(embed=log_embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при выключении системы работ: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)


def is_jobs_enabled():
    cursor.execute('SELECT jobs_enabled FROM jobs_settings WHERE id = 1')
    result = cursor.fetchone()
    return bool(result[0]) if result else False


async def check_user_job_status(user_id):
    cursor.execute('''
        SELECT j.id, j.name, j.is_government 
        FROM user_jobs uj
        JOIN jobs j ON uj.job_id = j.id
        WHERE uj.user_id = ?
    ''', (user_id,))
    
    job_info_list = cursor.fetchall()
    
    has_gov_job = any(job[2] for job in job_info_list)  
    has_non_gov_job = any(not job[2] for job in job_info_list)  
    
    return (has_gov_job, has_non_gov_job, job_info_list)

@tasks.loop(minutes=1)
async def check_promotion_eligibility():
    try:
        # Get all active shifts with promotion information
        cursor.execute('''
            SELECT a.user_id, a.job_id, a.start_time, j.promotion_time_hours, 
                   j.promotion_role_name, uj.worked_hours, j.name
            FROM active_shifts a
            JOIN jobs j ON a.job_id = j.id
            JOIN user_jobs uj ON a.job_id = uj.job_id AND a.user_id = uj.user_id
            WHERE j.promotion_time_hours > 0 AND j.promotion_role_name IS NOT NULL
        ''')
        
        active_shifts = cursor.fetchall()
        current_time = datetime.now()
        
        for shift in active_shifts:
            user_id, job_id, start_time, promotion_hours, promotion_role_name, worked_hours, job_name = shift
            
            # Calculate current shift duration
            start_time_dt = datetime.fromisoformat(start_time)
            current_shift_hours = (current_time - start_time_dt).total_seconds() / 3600
            
            # Calculate total hours (previous + current shift)
            total_hours = worked_hours + current_shift_hours
            
            # Check if user is eligible for promotion
            if total_hours >= promotion_hours:
                # Check if we've already notified this user
                cursor.execute('''
                    SELECT * FROM promotion_notifications 
                    WHERE user_id = ? AND job_id = ?
                ''', (user_id, job_id))
                
                notification = cursor.fetchone()
                
                if not notification:
                    # Send notification to user
                    try:
                        user = await bot.fetch_user(user_id)
                        
                        if user:
                            embed = disnake.Embed(
                                title="📈 Доступно повышение!",
                                description=(
                                    "━━━━━━━━━━ Карьерный рост ━━━━━━━━━━\n\n"
                                    f"🎉 **Поздравляем!** Вы отработали достаточно часов для повышения!\n"
                                    f"💼 **Текущая должность:** {job_name}\n"
                                    f"📈 **Новая должность:** {promotion_role_name}\n"
                                    f"⏰ **Отработано часов:** {total_hours:.1f}/{promotion_hours}\n\n"
                                    "⚠️ **Для получения повышения завершите текущую смену командой** `/работа завершить`\n\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                                ),
                                color=disnake.Color.gold()
                            )
                            
                            await user.send(embed=embed)
                            
                            # Record notification in database to avoid duplicate messages
                            cursor.execute('''
                                INSERT INTO promotion_notifications (user_id, job_id, notification_time)
                                VALUES (?, ?, ?)
                            ''', (user_id, job_id, current_time.isoformat()))
                            
                            conn.commit()
                    except Exception as e:
                        print(f"Failed to notify user about promotion: {e}")
        

    except Exception as e:
        print(f"Error in promotion check task: {e}")
        
async def check_license(user_id, required_license):
    if not required_license:
        return True, None
    cyrillic_to_latin = {
        'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E', 'Н': 'H', 'К': 'K',
        'М': 'M', 'О': 'O', 'Р': 'P', 'Т': 'T', 'Х': 'X', 'а': 'a',
        'в': 'b', 'с': 'c', 'е': 'e', 'н': 'h', 'к': 'k', 'м': 'm',
        'о': 'o', 'р': 'p', 'т': 't', 'х': 'x'
    }
    license_variants = [required_license]
    latin_variant = ''.join(cyrillic_to_latin.get(char, char) for char in required_license)
    if latin_variant != required_license:
        license_variants.append(latin_variant)
    latin_to_cyrillic = {v: k for k, v in cyrillic_to_latin.items()}
    cyrillic_variant = ''.join(latin_to_cyrillic.get(char, char) for char in required_license)
    if cyrillic_variant != required_license and cyrillic_variant not in license_variants:
        license_variants.append(cyrillic_variant)
    for variant in license_variants:
        cursor.execute('''
            SELECT * FROM licenses 
            WHERE user_id = ? 
            AND LOWER(TRIM(category)) = LOWER(TRIM(?)) 
            AND status = "active"
        ''', (str(user_id), variant))
        license_result = cursor.fetchone()
        if license_result:
            return True, license_result
    return False, None


@bot.command()
async def трудоустройство(ctx):
    try:
        has_gov_job, has_non_gov_job, job_info_list = await check_user_job_status(ctx.author.id)
        cursor.execute('''
            SELECT * FROM jobs 
            WHERE employability = 1
            ORDER BY hourly_pay
        ''')
        jobs = cursor.fetchall()
        if not jobs:
            embed = disnake.Embed(
                title="🔍 Нет доступных вакансий",
                description="В данный момент нет доступных вакансий",
                color=disnake.Color.red()
            )
            return await ctx.send(embed=embed)
        current_index = 0
        total_jobs = len(jobs)
        has_both_job_types = has_gov_job and has_non_gov_job
        async def show_job(index, interaction=None):
            job = jobs[index]
            job_is_government = job[3]
            meets_requirements = True
            requirements_text = ""
            if has_both_job_types:
                meets_requirements = False
                gov_job_name = "Неизвестно"
                non_gov_job_name = "Неизвестно"
                
                for job_info in job_info_list:
                    if job_info[2]: 
                        gov_job_name = job_info[1]
                    else: 
                        non_gov_job_name = job_info[1]
                requirements_text += f"❌ У вас уже есть максимальное количество работ:\n"
                requirements_text += f"• Государственная: **{gov_job_name}**\n"
                requirements_text += f"• Частная: **{non_gov_job_name}**\n"
            elif (job_is_government and has_gov_job) or (not job_is_government and has_non_gov_job):
                job_type_str = "государственной" if job_is_government else "частной"
                current_job_name = "Неизвестно"
                for job_info in job_info_list:
                    if job_info[2] == job_is_government:
                        current_job_name = job_info[1]
                        break
                meets_requirements = False
                requirements_text += f"❌ Вы уже работаете на {job_type_str} работе (**{current_job_name}**)\n"
            if job[4]:
                has_license, license_data = await check_license(ctx.author.id, job[4])   
                if not has_license:
                    meets_requirements = False
                    requirements_text += f"❌ Требуются права категории **{job[4]}**\n"
                else:
                    requirements_text += f"✅ Права категории **{job[4]}**\n"
            
            if job[5] > 0:
                has_license, license_data = await check_license(ctx.author.id, job[4])
                if license_data:
                    issue_date = datetime.fromisoformat(license_data[2])  
                    hours_since_issue = (datetime.now() - issue_date).total_seconds() / 3600
                    if hours_since_issue < job[5]:
                        meets_requirements = False
                        requirements_text += f"❌ Требуется **{job[5]}** часов опыта вождения (у вас {int(hours_since_issue)})\n"
                    else:
                        requirements_text += f"✅ **{int(job[5])}** часов опыта вождения\n"
                else:
                    meets_requirements = False
                    requirements_text += f"❌ Требуется **{job[5]}** часов опыта вождения\n"
            job_type = "Государственная" if job_is_government else "Частная"
            embed = disnake.Embed(
                title=f"💼 {job[1]}",
                description=(
                    "━━━━━━━━━━ Информация о вакансии ━━━━━━━━━━\n\n"
                    f"💰 **Оплата:** {'Сдельная' if job[2] == 0 else f'{job[2]:,}₽ в час'}\n"
                    f"🏢 **Тип работы:** {job_type}\n"
                ),
                color=disnake.Color.blue()
            )

            if requirements_text:
                embed.add_field(
                    name="📋 Требования",
                    value=requirements_text,
                    inline=False
                )
            if job[7]:  
                if job[9] == 0: 
                    embed.add_field(
                        name="📈 Карьерный рост",
                        value="**Максимальная должность**",
                        inline=False
                    )
                elif job[9] == 1: 
                    embed.add_field(
                        name="📈 Карьерный рост",
                        value=(
                            f"**Повышение до:** {job[7]}\n"
                            "**Примечание:** Повышение возможно только через модераторов"
                        ),
                        inline=False
                    )
                else: 
                    embed.add_field(
                        name="📈 Карьерный рост",
                        value=(
                            f"**Повышение до:** {job[7]}\n"
                            f"**Требуемое время работы:** {job[9]} часов"
                        ),
                        inline=False
                    )          
            if job_info_list:
                current_jobs_text = ""
                for job_info in job_info_list:
                    job_type_text = "Государственная" if job_info[2] else "Частная"
                    current_jobs_text += f"• **{job_info[1]}** ({job_type_text})\n"
                
                embed.add_field(
                    name="ℹ️ Текущие работы",
                    value=current_jobs_text,
                    inline=False
                )
            
            embed.set_footer(text=f"Вакансия {index + 1} из {total_jobs}")
            
            # Create view with navigation buttons
            view = disnake.ui.View(timeout=180)
            
            # Navigation buttons
            prev_button = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label="◀️ Предыдущая",
                disabled=index == 0
            )
            next_button = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                label="Следующая ▶️",
                disabled=index == total_jobs - 1
            )
            apply_button = disnake.ui.Button(
                style=disnake.ButtonStyle.green,
                label="✅ Устроиться",
                disabled=not meets_requirements
            )
            
            async def prev_callback(b_inter):
                nonlocal current_index
                current_index = max(0, current_index - 1)
                await b_inter.response.defer()
                await show_job(current_index, b_inter)
            
            async def next_callback(b_inter):
                nonlocal current_index
                current_index = min(total_jobs - 1, current_index + 1)
                await b_inter.response.defer()
                await show_job(current_index, b_inter)
            
            async def apply_callback(b_inter):
                await b_inter.response.defer()
                
                try:
                    job = jobs[current_index]
                    cursor.execute('''SELECT car FROM addjobs WHERE job_id=?''',(jobs[current_index][0],))
                    car_result = cursor.fetchone()
                    
                    # Check if car_result exists and extract the car name
                    car_name = car_result[0] if car_result else None
                    
                    # Only try to add car if car_name exists
                    if car_name:
                        addtoserverpo = await carmanager(b_inter.author.display_name, "добавить", car_name)
                        if addtoserverpo == False:
                            error_embed = disnake.Embed(
                                title="❌ Ошибка",
                                description=(
                                            "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                            "🚫 Не удалось добавить автомобиль на сервер\n"
                                            "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                                ),
                                color=disnake.Color.red()
                            )
                            await b_inter.edit_original_response(embed=error_embed, view=None)  
                            return
                    # Record employment in database
                    cursor.execute('''
                        INSERT INTO user_jobs (user_id, job_id, start_time)
                        VALUES (?, ?, ?)
                    ''', (b_inter.author.id, job[0], datetime.now().isoformat()))
                    
                    # Assign role if specified
                    if job[6]:  # role_id
                        # Handle both single role ID and comma-separated role IDs
                        if ',' in job[6]:
                            role_ids = job[6].split(',')
                        else:
                            role_ids = [job[6]]
                            
                        for role_id in role_ids:
                            try:
                                role = b_inter.guild.get_role(int(role_id.strip()))
                                if role:
                                    await b_inter.author.add_roles(role)
                            except Exception as e:
                                print(f"Error assigning role: {e}")
                    
                    conn.commit()
                    
                    success_embed = disnake.Embed(
                        title="✅ Вы успешно устроились на работу!",
                        description=(
                            "━━━━━━━━━━ Информация о трудоустройстве ━━━━━━━━━━\n\n"
                            f"💼 **Должность:** {job[1]}\n"
                            f"💰 **Оплата:** {job[2]:,}₽ в час\n"
                            f"🏢 **Тип работы:** {'Государственная' if job[3] else 'Частная'}\n"
                            f"📅 **Дата трудоустройства:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                            "Используйте команду `!начать_работу` чтобы начать смену\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.green()
                    )
                    
                    await b_inter.edit_original_response(embed=success_embed, view=None)
                    
                    # Log employment
                    logs_channel = bot.get_channel(1351455653197123665)
                    log_embed = disnake.Embed(
                        title="💼 Трудоустройство",
                        description=(
                            f"👤 **Игрок:** {b_inter.author.mention}\n"
                            f"💼 **Должность:** {job[1]}\n"
                            f"💰 **Оплата:** {job[2]:,}₽ в час\n"
                            f"🏢 **Тип работы:** {'Государственная' if job[3] else 'Частная'}\n"
                            f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                        ),
                        color=disnake.Color.blue()
                    )
                    await logs_channel.send(embed=log_embed)
                    
                except Exception as e:
                    error_embed = disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Произошла ошибка при трудоустройстве: {str(e)}",
                        color=disnake.Color.red()
                    )
                    await b_inter.edit_original_response(embed=error_embed)
            
            prev_button.callback = prev_callback
            next_button.callback = next_callback
            apply_button.callback = apply_callback
            
            view.add_item(prev_button)
            view.add_item(next_button)
            view.add_item(apply_button)
            
            if interaction:
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                return await ctx.send(embed=embed, view=view)
        
        # Show the first job
        await show_job(current_index)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении списка вакансий: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)

@bot.slash_command(name="работа", description="Управление работами и трудоустройством")
async def job_commands(inter: ApplicationCommandInteraction):
    """Группа команд для управления работами и трудоустройством"""
    pass

@job_commands.sub_command(name="список", description="Показать список ваших работ")
async def my_jobs(inter: ApplicationCommandInteraction):
    """Показывает список всех работ пользователя с возможностью увольнения"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Get all jobs for the user
        cursor.execute('''
            SELECT j.id, j.name, j.hourly_pay, j.is_government, uj.start_time, uj.worked_hours
            FROM user_jobs uj
            JOIN jobs j ON uj.job_id = j.id
            WHERE uj.user_id = ?
        ''', (inter.author.id,))
        
        jobs = cursor.fetchall()
        
        if not jobs:
            embed = disnake.Embed(
                title="💼 Мои работы",
                description="У вас нет активных работ. Используйте команду `/работа найти` для поиска работы.",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        # Initialize variables for pagination
        current_index = 0
        total_jobs = len(jobs)
        
        # Function to display job information
        async def show_job(index, interaction=None):
            job = jobs[index]
            job_id, job_name, hourly_pay, is_government, start_time, worked_hours = job
            
            # Calculate time worked
            start_date = datetime.fromisoformat(start_time)
            time_worked = datetime.now() - start_date
            days_worked = time_worked.days
            
            # Format worked hours
            worked_hours = worked_hours or 0
            
            # Check if promotion is available
            cursor.execute('''
                SELECT promotion_role_name, promotion_time_hours
                FROM jobs
                WHERE id = ?
            ''', (job_id,))
            
            promotion_info = cursor.fetchone()
            promotion_text = ""
            
            if promotion_info and promotion_info[0] and promotion_info[1]:
                promotion_role, promotion_hours = promotion_info
                remaining_hours = max(0, promotion_hours - worked_hours)
                progress = min(100, int((worked_hours / promotion_hours) * 100))
                
                promotion_text = (
                    f"📈 **Следующая должность:** {promotion_role}\n"
                    f"⏳ **Осталось часов:** {remaining_hours:.1f}\n"
                    f"📊 **Прогресс:** {progress}% ({worked_hours:.1f}/{promotion_hours})\n\n"
                )
            
            # Create embed with job information
            embed = disnake.Embed(
                title=f"💼 {job_name}",
                description=(
                    "━━━━━━━━━━ Информация о работе ━━━━━━━━━━\n\n"
                    f"💰 **Оплата:** {hourly_pay:,}₽/час\n"
                    f"🏢 **Тип:** {'Государственная' if is_government else 'Частная'}\n"
                    f"📅 **Дата трудоустройства:** {start_date.strftime('%d.%m.%Y')}\n"
                    f"⏱️ **Отработано дней:** {days_worked}\n"
                    f"⏱️ **Отработано часов:** {worked_hours:.1f}\n\n"
                    f"{promotion_text}"
                    f"📄 **Страница:** {index + 1}/{total_jobs}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.blue()
            )
            
            # Create navigation buttons
            view = disnake.ui.View(timeout=60)
            
            prev_button = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                emoji="⬅️",
                disabled=(index == 0)
            )
            
            next_button = disnake.ui.Button(
                style=disnake.ButtonStyle.secondary,
                emoji="➡️",
                disabled=(index == total_jobs - 1)
            )
            
            quit_button = disnake.ui.Button(
                style=disnake.ButtonStyle.danger,
                label="Уволиться",
                emoji="🚪"
            )
            
            async def prev_callback(b_inter):
                if b_inter.author.id != inter.author.id:
                    return await b_inter.response.send_message("Это не ваш список работ!", ephemeral=True)
                
                nonlocal current_index
                current_index = max(0, current_index - 1)
                await b_inter.response.defer()
                await show_job(current_index, b_inter)
            
            async def next_callback(b_inter):
                if b_inter.author.id != inter.author.id:
                    return await b_inter.response.send_message("Это не ваш список работ!", ephemeral=True)
                
                nonlocal current_index
                current_index = min(total_jobs - 1, current_index + 1)
                await b_inter.response.defer()
                await show_job(current_index, b_inter)
            
            async def quit_callback(b_inter):
                if b_inter.author.id != inter.author.id:
                    return await b_inter.response.send_message("Это не ваш список работ!", ephemeral=True)
                
                # Create confirmation view
                confirm_view = disnake.ui.View(timeout=30)
                
                confirm_button = disnake.ui.Button(
                    style=disnake.ButtonStyle.danger,
                    label="Подтвердить",
                    emoji="✅"
                )
                
                cancel_button = disnake.ui.Button(
                    style=disnake.ButtonStyle.secondary,
                    label="Отмена",
                    emoji="❌"
                )
                
                async def confirm_quit(c_inter):
                    if c_inter.author.id != inter.author.id:
                        return await c_inter.response.send_message("Это не ваше увольнение!", ephemeral=True)
                    
                    await c_inter.response.defer()
                    
                    try:
                        # Check if user has an active shift for this job
                        cursor.execute('SELECT * FROM active_shifts WHERE user_id = ? AND job_id = ?', 
                                      (inter.author.id, job_id))
                        active_shift = cursor.fetchone()
                        
                        if active_shift:
                            error_embed = disnake.Embed(
                                title="❌ Ошибка",
                                description="Вы не можете уволиться во время активной смены. Сначала завершите смену.",
                                color=disnake.Color.red()
                            )
                            return await c_inter.edit_original_response(embed=error_embed, view=None)
                        
                        # Get job role IDs
                        cursor.execute('SELECT role_id FROM jobs WHERE id = ?', (job_id,))
                        role_ids = cursor.fetchone()[0]
                        
                        # Remove roles if specified
                        if role_ids:
                            for role_id in role_ids.split(','):
                                try:
                                    role = inter.guild.get_role(int(role_id.strip()))
                                    if role:
                                        await inter.author.remove_roles(role)
                                except Exception as e:
                                    print(f"Error removing role: {e}")
                        
                        # Delete job from user_jobs
                        cursor.execute('DELETE FROM user_jobs WHERE user_id = ? AND job_id = ?', 
                                      (inter.author.id, job_id))
                        conn.commit()
                        
                        quit_embed = disnake.Embed(
                            title="✅ Увольнение выполнено",
                            description=(
                                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                f"💼 **Должность:** {job_name}\n"
                                f"⏱️ **Отработано часов:** {worked_hours:.1f}\n"
                                f"📅 **Дата увольнения:** {datetime.now().strftime('%d.%m.%Y')}\n\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ),
                            color=disnake.Color.green()
                        )
                        
                        await c_inter.edit_original_response(embed=quit_embed, view=None)
                        
                        # Log the quit
                        logs_channel = bot.get_channel(1351455653197123665)
                        log_embed = disnake.Embed(
                            title="🚪 Увольнение с работы",
                            description=(
                                f"👤 **Игрок:** {inter.author.mention}\n"
                                f"💼 **Должность:** {job_name}\n"
                                f"⏰ **Отработано часов:** {worked_hours:.1f}\n"
                                f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                            ),
                            color=disnake.Color.red()
                        )
                        await logs_channel.send(embed=log_embed)
                        
                        # Check if there are any remaining jobs
                        cursor.execute('SELECT COUNT(*) FROM user_jobs WHERE user_id = ?', (inter.author.id,))
                        remaining_jobs = cursor.fetchone()[0]
                        
                        if remaining_jobs > 0:
                            # Refresh the jobs list
                            cursor.execute('''
                                SELECT j.id, j.name, j.hourly_pay, j.is_government, uj.start_time, uj.worked_hours
                                FROM user_jobs uj
                                JOIN jobs j ON uj.job_id = j.id
                                WHERE uj.user_id = ?
                            ''', (inter.author.id,))
                            
                            nonlocal jobs, total_jobs, current_index
                            jobs = cursor.fetchall()
                            total_jobs = len(jobs)
                            current_index = 0
                            
                            # Show the updated job list
                            await show_job(0, interaction)
                        
                    except Exception as e:
                        error_embed = disnake.Embed(
                            title="❌ Ошибка",
                            description=f"Произошла ошибка при увольнении: {str(e)}",
                            color=disnake.Color.red()
                        )
                        await c_inter.edit_original_response(embed=error_embed)
                
                async def cancel_quit(c_inter):
                    if c_inter.author.id != inter.author.id:
                        return await c_inter.response.send_message("Это не ваше увольнение!", ephemeral=True)
                    
                    await c_inter.response.defer()
                    await show_job(current_index, c_inter)
                
                confirm_button.callback = confirm_quit
                cancel_button.callback = cancel_quit
                
                confirm_view.add_item(confirm_button)
                confirm_view.add_item(cancel_button)
                
                confirm_embed = disnake.Embed(
                    title="⚠️ Подтверждение увольнения",
                    description=(
                        "━━━━━━━━━━ Внимание ━━━━━━━━━━\n\n"
                        f"Вы действительно хотите уволиться с должности **{job_name}**?\n\n"
                        "⚠️ **Это действие необратимо!**\n"
                        "⚠️ **Весь прогресс карьерного роста будет потерян!**\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.yellow()
                )
                
                await b_inter.response.send_message(embed=confirm_embed, view=confirm_view, ephemeral=True)
            
            prev_button.callback = prev_callback
            next_button.callback = next_callback
            quit_button.callback = quit_callback
            
            view.add_item(prev_button)
            view.add_item(next_button)
            view.add_item(quit_button)
            
            if interaction:
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                return await inter.edit_original_response(embed=embed, view=view)
        
        # Show the first job
        await show_job(current_index)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении списка работ: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@job_commands.sub_command(name="начать", description="Начать рабочую смену")
async def start_work(inter: ApplicationCommandInteraction):
    """Начать рабочую смену на одной из ваших работ"""
    try:
        await inter.response.defer(ephemeral=True)
        
        if not is_jobs_enabled():
            # Get player data to provide more specific information
            try:
                # Read player data from file
                # Get the script directory path
                script_dir = os.path.dirname(os.path.abspath(__file__))
                file_path = os.path.join(script_dir, 'latest_players.json')

                with open(file_path, 'r', encoding='utf-8') as f:
                    player_data = json.load(f)
                
                # Handle the specific format: {"playerCount":X,"players":{"0":{"vehicles":[...],"name":"..."}}}
                if isinstance(player_data, dict) and "playerCount" in player_data and "players" in player_data:
                    total_players = player_data["playerCount"]
                    players_dict = player_data["players"]
                    
                    # Get moderator count
                    moderator_count = sum(1 for _, p in players_dict.items() 
                                         if p.get('name') in BEAMMP_MODERATORS)
                    
                    # Create a more specific message based on the reason
                    reason = ""
                    if total_players < 3:
                        reason = f"Недостаточно игроков на сервере (сейчас: {total_players}, нужно: 4)"
                    elif moderator_count < 1:
                        reason = f"На сервере нет модераторов (нужен хотя бы 1)"
                    else:
                        reason = "Система отключена администрацией"
                        
                    embed = disnake.Embed(
                        title="🚫 Система работ отключена",
                        description=f"В данный момент система работ недоступна\n**Причина:** {reason}",
                        color=disnake.Color.red()
                    )
                    return await inter.edit_original_response(embed=embed)
                # Handle list format as fallback
                elif isinstance(player_data, list):
                    total_players = len(player_data)
                    moderator_count = sum(1 for p in player_data 
                                         if isinstance(p, dict) and p.get('name') in BEAMMP_MODERATORS)
                    
                    reason = ""
                    if total_players < 4:
                        reason = f"Недостаточно игроков на сервере (сейчас: {total_players}, нужно: 4)"
                    elif moderator_count < 1:
                        reason = f"На сервере нет модераторов (нужен хотя бы 1)"
                    else:
                        reason = "Система отключена администрацией"
                        
                    embed = disnake.Embed(
                        title="🚫 Система работ отключена",
                        description=f"В данный момент система работ недоступна\n**Причина:** {reason}",
                        color=disnake.Color.red()
                    )
                    return await inter.edit_original_response(embed=embed)
            except Exception as e:
                print(f"Error getting player data: {e}")
            
            # Fallback message if player data couldn't be retrieved
            embed = disnake.Embed(
                title="🚫 Система работ отключена",
                description="В данный момент система работ отключена\nНеобходимо минимум 4 игрока и 1 модератор на сервере",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        # Check if user already has an active shift
        cursor.execute('SELECT * FROM active_shifts WHERE user_id = ?', (inter.author.id,))
        active_shift = cursor.fetchone()
        
        if active_shift:
            # Calculate time worked so far
            start_time = datetime.fromisoformat(active_shift[2])
            time_worked = datetime.now() - start_time
            hours_worked = time_worked.total_seconds() / 3600
            
            embed = disnake.Embed(
                title="⚠️ Смена уже начата",
                description=(
                    "━━━━━━━━━━ Информация о смене ━━━━━━━━━━\n\n"
                    f"⏰ **Начало смены:** {start_time.strftime('%d.%m.%Y %H:%M')}\n"
                    f"⌛ **Прошло времени:** {int(time_worked.total_seconds() // 3600)}ч {int((time_worked.total_seconds() % 3600) // 60)}мин\n\n"
                    "Чтобы закончить смену, используйте команду `/работа завершить`\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.yellow()
            )
            return await inter.edit_original_response(embed=embed)
        
        # Check if user has a job
        cursor.execute('''
            SELECT j.id, j.name, j.hourly_pay
            FROM user_jobs uj
            JOIN jobs j ON uj.job_id = j.id
            WHERE uj.user_id = ?
        ''', (inter.author.id,))
        
        jobs = cursor.fetchall()
        
        if not jobs:
            embed = disnake.Embed(
                title="❌ Нет работы",
                description="У вас нет работы. Используйте команду `/работа найти` для поиска работы.",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        # If user has multiple jobs, let them choose
        if len(jobs) > 1:
            # Create embed with job options
            embed = disnake.Embed(
                title="💼 Выберите работу",
                description="У вас несколько работ. Выберите, на какой работе вы хотите начать смену:",
                color=disnake.Color.blue()
            )
            
            # Create view with job selection buttons
            view = disnake.ui.View(timeout=60)
            
            for job in jobs:
                job_id, job_name, hourly_pay = job
                
                # Create button for each job
                job_button = disnake.ui.Button(
                    style=disnake.ButtonStyle.primary,
                    label=f"{job_name} ({hourly_pay}₽/ч)",
                    custom_id=str(job_id)
                )
                
                async def job_button_callback(interaction, selected_job_id=job_id, selected_job_name=job_name):
                    if interaction.author.id != inter.author.id:
                        return await interaction.response.send_message("Это не ваша смена!", ephemeral=True)
                    
                    await interaction.response.defer()
                    
                    # Start shift for selected job
                    now = datetime.now()
                    cursor.execute(
                        'INSERT INTO active_shifts (user_id, job_id, start_time) VALUES (?, ?, ?)',
                        (inter.author.id, selected_job_id, now.isoformat())
                    )
                    conn.commit()
                    
                    success_embed = disnake.Embed(
                        title="✅ Смена начата",
                        description=(
                            "━━━━━━━━━━ Информация о смене ━━━━━━━━━━\n\n"
                            f"💼 **Работа:** {selected_job_name}\n"
                            f"⏰ **Начало смены:** {now.strftime('%d.%m.%Y %H:%M')}\n\n"
                            "Чтобы закончить смену, используйте команду `/работа завершить`\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.green()
                    )
                    
                    await interaction.edit_original_response(embed=success_embed, view=None)
                
                job_button.callback = lambda i, jid=job_id, jname=job_name: job_button_callback(i, jid, jname)
                view.add_item(job_button)
            
            return await inter.edit_original_response(embed=embed, view=view)
        
        # If user has only one job, start shift for that job
        job_id, job_name, hourly_pay = jobs[0]
        
        now = datetime.now()
        cursor.execute(
            'INSERT INTO active_shifts (user_id, job_id, start_time) VALUES (?, ?, ?)',
            (inter.author.id, job_id, now.isoformat())
        )
        conn.commit()
        
        embed = disnake.Embed(
            title="✅ Смена начата",
            description=(
                "━━━━━━━━━━ Информация о смене ━━━━━━━━━━\n\n"
                f"💼 **Работа:** {job_name}\n"
                f"⏰ **Начало смены:** {now.strftime('%d.%m.%Y %H:%M')}\n\n"
                "Чтобы закончить смену, используйте команду `/работа завершить`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        
        await inter.edit_original_response(embed=embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при начале смены: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@job_commands.sub_command(name="статус", description="Показать информацию о текущей смене")
async def shift_status(inter: ApplicationCommandInteraction):
    """Показать информацию о текущей рабочей смене"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Check if user has an active shift
        cursor.execute('''
            SELECT a.job_id, a.start_time, j.hourly_pay, j.name, j.promotion_role_name, 
                   j.promotion_time_hours, uj.worked_hours
            FROM active_shifts a
            JOIN jobs j ON a.job_id = j.id
            JOIN user_jobs uj ON a.job_id = uj.job_id AND a.user_id = uj.user_id
            WHERE a.user_id = ?
        ''', (inter.author.id,))
        
        shift_data = cursor.fetchone()
        
        if not shift_data:
            embed = disnake.Embed(
                title="❌ Нет активной смены",
                description="У вас нет активной смены. Используйте команду `/работа начать` для начала работы.",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        job_id, start_time, hourly_pay, job_name, promotion_role_name, promotion_hours, worked_hours = shift_data
        
        # Calculate current shift duration and earnings
        start_time_dt = datetime.fromisoformat(start_time)
        current_time = datetime.now()
        time_worked = current_time - start_time_dt
        hours_worked = time_worked.total_seconds() / 3600
        current_earnings = int(hours_worked * hourly_pay)
        
        # Create promotion progress information
        promotion_info = ""
        if promotion_role_name and promotion_hours > 0:
            total_hours = worked_hours + hours_worked
            remaining_hours = max(0, promotion_hours - total_hours)
            progress = min(100, int((total_hours / promotion_hours) * 100))
            
            promotion_info = (
                "━━━━━━━━━━ Прогресс повышения ━━━━━━━━━━\n\n"
                f"📈 **Следующая должность:** {promotion_role_name}\n"
                f"⏳ **Осталось часов:** {remaining_hours:.1f}\n"
                f"📊 **Прогресс:** {progress}% ({total_hours:.1f}/{promotion_hours})\n\n"
            )
        
        # Create embed with shift information
        embed = disnake.Embed(
            title="📊 Информация о текущей смене",
            description=(
                "━━━━━━━━━━ Информация о смене ━━━━━━━━━━\n\n"
                f"💼 **Работа:** {job_name}\n"
                f"⏰ **Начало смены:** {start_time_dt.strftime('%d.%m.%Y %H:%M')}\n"
                f"⌛ **Длительность:** {int(time_worked.total_seconds() // 3600)}ч {int((time_worked.total_seconds() % 3600) // 60)}мин\n"
                f"💰 **Заработано за смену:** {current_earnings:,}₽\n"
                f"💵 **Почасовая оплата:** {hourly_pay:,}₽\n\n"
                f"{promotion_info}"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.blue()
        )
        
        await inter.edit_original_response(embed=embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении информации о смене: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@job_commands.sub_command(name="завершить", description="Завершить рабочую смену и получить оплату")
async def end_work(inter: ApplicationCommandInteraction):
    """Завершить рабочую смену и получить оплату"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Check if jobs system is enabled
        if not is_jobs_enabled():
            embed = disnake.Embed(
                title="🚫 Система работ отключена",
                description="В данный момент система работ отключена администрацией",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        # Check if user has an active shift
        cursor.execute('''
            SELECT a.job_id, a.start_time, j.hourly_pay, j.name, j.promotion_role_name, 
                   j.promotion_time_hours, j.promotion_role_id, j.role_id, uj.worked_hours
            FROM active_shifts a
            JOIN jobs j ON a.job_id = j.id
            JOIN user_jobs uj ON a.job_id = uj.job_id AND a.user_id = uj.user_id
            WHERE a.user_id = ?
        ''', (inter.author.id,))
        
        shift_data = cursor.fetchone()
        
        if not shift_data:
            embed = disnake.Embed(
                title="❌ Нет активной смены",
                description="У вас нет активной смены. Используйте команду `/работа начать` для начала работы.",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        job_id, start_time, hourly_pay, job_name, promotion_role_name, promotion_hours, promotion_role_id, current_role_id, previous_worked_hours = shift_data
        
        # Calculate time worked and payment
        start_time_dt = datetime.fromisoformat(start_time)
        end_time_dt = datetime.now()
        time_worked = end_time_dt - start_time_dt
        hours_worked = time_worked.total_seconds() / 3600
        payment = int(hours_worked * hourly_pay)
        
        # Update user's balance
        bal = unbclient.get_user_bal(1341469479510474813, inter.author.id)
        new_bal = bal['cash'] + payment
        unbclient.set_user_bal(1341469479510474813, inter.author.id, cash=new_bal)
        
        # Update worked hours in user_jobs
        total_worked_hours = previous_worked_hours + hours_worked
        cursor.execute('''
            UPDATE user_jobs 
            SET worked_hours = ? 
            WHERE user_id = ? AND job_id = ?
        ''', (total_worked_hours, inter.author.id, job_id))
        
        # Remove active shift
        cursor.execute('DELETE FROM active_shifts WHERE user_id = ?', (inter.author.id,))
        conn.commit()
        
        # Check for promotion eligibility
        promotion_message = ""
        if promotion_role_name and promotion_hours > 0 and total_worked_hours >= promotion_hours:
            # User is eligible for promotion
            promotion_message = (
                "━━━━━━━━━━ Повышение ━━━━━━━━━━\n\n"
                f"🎉 **Поздравляем!** Вы отработали достаточно часов для повышения!\n"
                f"📈 **Новая должность:** {promotion_role_name}\n\n"
            )
            
            # Update user's job role
            if promotion_role_id:
                # Remove current role(s)
                if current_role_id:
                    current_role_ids = current_role_id.split(',')
                    for role_id in current_role_ids:
                        try:
                            role = inter.guild.get_role(int(role_id.strip()))
                            if role:
                                await inter.author.remove_roles(role)
                        except Exception as e:
                            print(f"Error removing role: {e}")
                
                # Add promotion role(s)
                promotion_role_ids = promotion_role_id.split(',')
                for role_id in promotion_role_ids:
                    try:
                        role = inter.guild.get_role(int(role_id.strip()))
                        if role:
                            await inter.author.add_roles(role)
                    except Exception as e:
                        print(f"Error adding promotion role: {e}")
                
                # Update job record with new role
                cursor.execute('''
                    UPDATE user_jobs 
                    SET worked_hours = 0 
                    WHERE user_id = ? AND job_id = ?
                ''', (inter.author.id, job_id))
                conn.commit()
                
                # Get car for the job
                cursor.execute('''SELECT car FROM addjobs WHERE job_id=?''', (job_id,))
                car_result = cursor.fetchone()
                if car_result:
                    car = car_result[0]
                    # Remove car from server
                    addtoserverpr = await carmanager(inter.author.display_name, "удалить", car)
                    if addtoserverpr == False:
                        error_embed = disnake.Embed(
                            title="❌ Ошибка",
                            description=(
                                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                "🚫 Не удалось удалить автомобиль с сервера\n"
                                "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ),
                            color=disnake.Color.red()
                        )
                        await inter.edit_original_response(embed=error_embed)
                
                # Get the next job in the promotion path
                cursor.execute('''
                    SELECT id FROM jobs 
                    WHERE role_id = ?
                ''', (promotion_role_id,))
                
                next_job = cursor.fetchone()
                
                if next_job:
                    # Update user's job to the promoted position
                    cursor.execute('''
                        UPDATE user_jobs 
                        SET job_id = ? 
                        WHERE user_id = ? AND job_id = ?
                    ''', (next_job[0], inter.author.id, job_id))
                    
                    # Get car for the new job
                    cursor.execute('''SELECT car FROM addjobs WHERE job_id=?''', (next_job[0],))
                    new_car_result = cursor.fetchone()
                    if new_car_result:
                        new_car = new_car_result[0]
                        # Add new car to server
                        addtoserverpo = await carmanager(inter.author.display_name, "добавить", new_car)
                        if addtoserverpo == False:
                            error_embed = disnake.Embed(
                                title="❌ Ошибка",
                                description=(
                                    "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                    "🚫 Не удалось добавить автомобиль на сервер\n"
                                    "👨‍💼 Пожалуйста, свяжитесь с администрацией\n\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                                ),
                                color=disnake.Color.red()
                            )
                            await inter.edit_original_response(embed=error_embed)
                
                conn.commit()
                
                # Log the promotion
                logs_channel = bot.get_channel(1351455653197123665)
                promotion_log_embed = disnake.Embed(
                    title="📈 Повышение на работе",
                    description=(
                        f"👤 **Игрок:** {inter.author.mention}\n"
                        f"💼 **Предыдущая должность:** {job_name}\n"
                        f"📈 **Новая должность:** {promotion_role_name}\n"
                        f"⏰ **Отработано часов:** {total_worked_hours:.1f}\n"
                        f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                    ),
                    color=disnake.Color.gold()
                )
                await logs_channel.send(embed=promotion_log_embed)
        
        # Create success embed
        embed = disnake.Embed(
            title="✅ Смена завершена",
            description=(
                "━━━━━━━━━━ Информация о смене ━━━━━━━━━━\n\n"
                f"💼 **Работа:** {job_name}\n"
                f"⏰ **Начало смены:** {start_time_dt.strftime('%d.%m.%Y %H:%M')}\n"
                f"⌛ **Продолжительность:** {int(time_worked.total_seconds() // 3600)}ч {int((time_worked.total_seconds() % 3600) // 60)}мин\n"
                f"💰 **Заработано:** {payment:,}₽\n"
                f"📊 **Всего отработано часов:** {total_worked_hours:.1f}\n\n"
                f"{promotion_message}"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        
        await inter.edit_original_response(embed=embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при завершении смены: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@job_commands.sub_command_group(
    name="админ",
    description="Команды администрирования работ"
)
async def job_admin(inter: ApplicationCommandInteraction):
    """Группа команд администрирования работ"""
    pass

@job_admin.sub_command(name="добавить", description="Добавить работу игроку")
@commands.has_any_role("Модератор", "Высшее руководство")
async def add_job_to_player(inter: ApplicationCommandInteraction, 
                           member: disnake.Member = commands.Param(description="Игрок"),
                           job_id: int = commands.Param(description="ID работы")):
    """Добавить работу указанному игроку"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Check if job exists
        cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
        job = cursor.fetchone()
        
        if not job:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description="Работа с указанным ID не найдена",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        # Check if user already has this job
        cursor.execute('SELECT * FROM user_jobs WHERE user_id = ? AND job_id = ?', 
                      (member.id, job_id))
        existing_job = cursor.fetchone()
        
        if existing_job:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"{member.mention} уже работает на этой должности",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        # Check if user has a job of the same type (government/non-government)
        cursor.execute('''
            SELECT j.name, j.is_government 
            FROM user_jobs uj
            JOIN jobs j ON uj.job_id = j.id
            WHERE uj.user_id = ? AND j.is_government = ?
        ''', (member.id, job[3]))  # job[3] is is_government field
        
        existing_type_job = cursor.fetchone()
        
        if existing_type_job:
            job_type = "государственную" if job[3] else "частную"
            embed = disnake.Embed(
                title="❌ Ошибка",
                description=(
                    f"{member.mention} уже имеет {job_type} работу: **{existing_type_job[0]}**\n"
                    "Сначала необходимо уволить игрока с текущей работы"
                ),
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        # Add job to user
        cursor.execute('''
            INSERT INTO user_jobs (user_id, job_id, start_time)
            VALUES (?, ?, ?)
        ''', (member.id, job_id, datetime.now().isoformat()))
        
        # Assign role if specified
        if job[6]:  # role_id field
            role_ids = job[6].split(',')
            for role_id in role_ids:
                try:
                    role = inter.guild.get_role(int(role_id.strip()))
                    if role:
                        await member.add_roles(role)
                except Exception as e:
                    print(f"Error assigning role: {e}")
        
        conn.commit()
        
        # Create success embed
        embed = disnake.Embed(
            title="✅ Работа добавлена",
            description=(
                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                f"👤 **Игрок:** {member.mention}\n"
                f"💼 **Должность:** {job[1]}\n"
                f"💰 **Оплата:** {job[2]:,}₽/час\n"
                f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        
        await inter.edit_original_response(embed=embed)
        
        # Log the action
        logs_channel = bot.get_channel(1351455653197123665)
        log_embed = disnake.Embed(
            title="💼 Добавление работы",
            description=(
                f"👤 **Игрок:** {member.mention}\n"
                f"💼 **Должность:** {job[1]}\n"
                f"👮 **Модератор:** {inter.author.mention}\n"
                f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            color=disnake.Color.blue()
        )
        await logs_channel.send(embed=log_embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при добавлении работы: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@job_admin.sub_command(name="завершить", description="Принудительно завершить смену игрока")
@commands.has_any_role('Смотрящий за RolePlay',"Модератор", "Высшее руководство")
async def force_end_work(inter: ApplicationCommandInteraction,
                        member: disnake.Member = commands.Param(description="Игрок")):
    """Принудительно завершить рабочую смену указанного игрока"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Check if user has an active shift
        cursor.execute('''
            SELECT a.job_id, a.start_time, j.hourly_pay, j.name
            FROM active_shifts a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.user_id = ?
        ''', (member.id,))
        
        shift_data = cursor.fetchone()
        
        if not shift_data:
            embed = disnake.Embed(
                title="❌ Нет активной смены",
                description=f"У {member.mention} нет активной смены",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        job_id, start_time, hourly_pay, job_name = shift_data
        
        # Calculate payment for worked time
        start_time_dt = datetime.fromisoformat(start_time)
        end_time_dt = datetime.now()
        time_worked = end_time_dt - start_time_dt
        hours_worked = time_worked.total_seconds() / 3600
        payment = int(hours_worked * hourly_pay)
        
        # Update user's balance
        bal = unbclient.get_user_bal(1341469479510474813, member.id)
        new_bal = bal['cash'] + payment
        unbclient.set_user_bal(1341469479510474813, member.id, cash=new_bal)
        
        # Update worked hours in user_jobs
        cursor.execute('''
            SELECT worked_hours FROM user_jobs 
            WHERE user_id = ? AND job_id = ?
        ''', (member.id, job_id))
        previous_worked_hours = cursor.fetchone()[0] or 0
        total_worked_hours = previous_worked_hours + hours_worked
        
        cursor.execute('''
            UPDATE user_jobs 
            SET worked_hours = ? 
            WHERE user_id = ? AND job_id = ?
        ''', (total_worked_hours, member.id, job_id))
        
        # Remove active shift
        cursor.execute('DELETE FROM active_shifts WHERE user_id = ?', (member.id,))
        conn.commit()
        
        # Create success embed
        embed = disnake.Embed(
            title="✅ Смена принудительно завершена",
            description=(
                "━━━━━━━━━━ Информация о смене ━━━━━━━━━━\n\n"
                f"👤 **Игрок:** {member.mention}\n"
                f"💼 **Работа:** {job_name}\n"
                f"⏰ **Начало смены:** {start_time_dt.strftime('%d.%m.%Y %H:%M')}\n"
                f"⌛ **Продолжительность:** {int(time_worked.total_seconds() // 3600)}ч {int((time_worked.total_seconds() % 3600) // 60)}мин\n"
                f"💰 **Заработано:** {payment:,}₽\n"
                f"👮 **Модератор:** {inter.author.mention}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        
        await inter.edit_original_response(embed=embed)
        
        # Log the action
        logs_channel = bot.get_channel(1351455653197123665)
        log_embed = disnake.Embed(
            title="⚠️ Принудительное завершение смены",
            description=(
                f"👤 **Игрок:** {member.mention}\n"
                f"💼 **Работа:** {job_name}\n"
                f"⏰ **Продолжительность:** {int(time_worked.total_seconds() // 3600)}ч {int((time_worked.total_seconds() % 3600) // 60)}мин\n"
                f"💰 **Заработано:** {payment:,}₽\n"
                f"👮 **Модератор:** {inter.author.mention}\n"
                f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            color=disnake.Color.orange()
        )
        await logs_channel.send(embed=log_embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при завершении смены: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@job_admin.sub_command(name="удалить", description="Удалить работу у игрока")
@commands.has_any_role("Модератор", "Высшее руководство")
async def remove_job_from_player(inter: ApplicationCommandInteraction, 
                                member: disnake.Member = commands.Param(description="Игрок"),
                                job_id: int = commands.Param(description="ID работы")):
    """Удалить работу у указанного игрока"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Check if player has an active shift
        cursor.execute('SELECT * FROM active_shifts WHERE user_id = ?', (member.id,))
        active_shift = cursor.fetchone()
        
        if active_shift:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description=(
                    f"{member.mention} сейчас работает.\n"
                    "Дождитесь окончания смены или используйте команду `/работа админ завершить`"
                ),
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)

        # Check if job exists and player has it
        cursor.execute('''
            SELECT j.name, j.role_id 
            FROM user_jobs uj
            JOIN jobs j ON uj.job_id = j.id
            WHERE uj.user_id = ? AND uj.job_id = ?
        ''', (member.id, job_id))
        
        job = cursor.fetchone()
        
        if not job:
            embed = disnake.Embed(
                title="❌ Ошибка",
                description=f"{member.mention} не работает на указанной должности",
                color=disnake.Color.red()
            )
            return await inter.edit_original_response(embed=embed)
        
        job_name, role_ids = job

        # Remove job from user
        cursor.execute('DELETE FROM user_jobs WHERE user_id = ? AND job_id = ?', 
                      (member.id, job_id))
        
        # Remove associated roles if specified
        if role_ids:
            for role_id in role_ids.split(','):
                try:
                    role = inter.guild.get_role(int(role_id.strip()))
                    if role:
                        await member.remove_roles(role)
                except Exception as e:
                    print(f"Error removing role: {e}")
        
        conn.commit()
        
        # Create success embed
        embed = disnake.Embed(
            title="✅ Работа удалена",
            description=(
                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                f"👤 **Игрок:** {member.mention}\n"
                f"💼 **Должность:** {job_name}\n"
                f"👮 **Модератор:** {inter.author.mention}\n"
                f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        
        await inter.edit_original_response(embed=embed)
        
        # Log the action
        logs_channel = bot.get_channel(1351455653197123665)
        log_embed = disnake.Embed(
            title="🗑️ Удаление работы",
            description=(
                f"👤 **Игрок:** {member.mention}\n"
                f"💼 **Должность:** {job_name}\n"
                f"👮 **Модератор:** {inter.author.mention}\n"
                f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            color=disnake.Color.red()
        )
        await logs_channel.send(embed=log_embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при удалении работы: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)


@job_admin.sub_command(name="смены", description="Просмотр всех активных рабочих смен")
@commands.has_any_role('Смотрящий за RolePlay',"Модератор", "Высшее руководство")
async def active_shifts(inter: ApplicationCommandInteraction):
    """Slash command for moderators to view all active work shifts"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Get all active shifts with detailed information
        cursor.execute('''
            SELECT 
                a.user_id,
                a.job_id,
                a.start_time,
                j.name AS job_name,
                j.hourly_pay,
                u.worked_hours
            FROM active_shifts a
            JOIN jobs j ON a.job_id = j.id
            JOIN user_jobs u ON a.job_id = u.job_id AND a.user_id = u.user_id
            ORDER BY a.start_time ASC
        ''')
        
        active_shifts = cursor.fetchall()
        
        if not active_shifts:
            embed = disnake.Embed(
                title="📊 Активные смены",
                description="В данный момент нет активных смен",
                color=disnake.Color.blue()
            )
            return await inter.edit_original_response(embed=embed)
        
        # Create embed
        embed = disnake.Embed(
            title="📊 Активные смены",
            description=f"Всего активных смен: {len(active_shifts)}",
            color=disnake.Color.blue()
        )
        
        current_time = datetime.now()
        
        # Add field for each active shift
        for shift in active_shifts:
            user_id, job_id, start_time, job_name, hourly_pay, worked_hours = shift
            
            try:
                # Get user object
                user = await bot.fetch_user(user_id)
                user_mention = user.mention
            except:
                user_mention = f"ID: {user_id}"
            
            # Calculate shift duration
            start_time_dt = datetime.fromisoformat(start_time)
            duration = current_time - start_time_dt
            hours = duration.total_seconds() / 3600
            
            # Calculate earnings for this shift
            earnings = int(hours * hourly_pay)
            
            # Format duration
            hours_worked = int(duration.total_seconds() // 3600)
            minutes_worked = int((duration.total_seconds() % 3600) // 60)
            
            embed.add_field(
                name=f"👤 {user_mention}",
                value=(
                    f"💼 **Должность:** {job_name}\n"
                    f"⏰ **Начало смены:** {start_time_dt.strftime('%H:%M')}\n"
                    f"⌛ **Длительность:** {hours_worked}ч {minutes_worked}мин\n"
                    f"💰 **Заработано:** {earnings:,}₽\n"
                    f"📊 **Всего отработано:** {(worked_hours + hours):.1f}ч"
                ),
                inline=False
            )
        
        embed.set_footer(text=f"Данные обновлены: {current_time.strftime('%d.%m.%Y %H:%M')}")
        
        # Send embed
        await inter.edit_original_response(embed=embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при получении информации о сменах: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)

@bot.command()
async def players(ctx):
    processing_msg = await ctx.send(
        embed=disnake.Embed(
            title="⏳ Загрузка данных игроков...",
            description="Получение информации с сервера...",
            color=disnake.Color.blue()
        )
    )
    
    try:
        download_file_from_server()
        

        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'latest_players.json')
        

        cars_file_path = os.path.join(script_dir, 'cars.json')
        car_names = {}
        try:
            with open(cars_file_path, 'r', encoding='utf-8') as f:
                car_names = json.load(f)
        except Exception as e:
            print(f"Error loading cars.json: {e}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                player_data = json.load(f)
                

            embed = disnake.Embed(
                title="🎮 Информация об игроках на сервере",
                color=disnake.Color.green()
            )
            

            if isinstance(player_data, dict) and "playerCount" in player_data and "players" in player_data:
                total_players = player_data["playerCount"]
                players_dict = player_data["players"]
                
                embed.description = f"Всего игроков онлайн: **{total_players}**"
                
                if not players_dict:
                    embed.add_field(
                        name="ℹ️ Информация",
                        value="На сервере нет игроков в данный момент.",
                        inline=False
                    )
                else:

                    for player_id, player_info in players_dict.items():
                        player_name = player_info.get("name", f"Player {player_id}")
                        vehicles = player_info.get("vehicles", [])
                        

                        field_value = f"🆔 **ID:** {player_id}\n"
                        

                        if vehicles:
                            vehicle_count = len(vehicles)
                            field_value += f"🚗 **Транспорт:** {vehicle_count} шт.\n"
                            

                            field_value += "```\n"
                            for i, vehicle in enumerate(vehicles[:5], 1):
                                parts = vehicle.split('/')
                                base_vehicle = parts[1] if len(parts) > 1 else vehicle
                                

                                proper_name = car_names.get(base_vehicle, base_vehicle)
                                

                                field_value += f"{i}. {proper_name}\n"

                            if len(vehicles) > 5:
                                field_value += f"...и еще {len(vehicles) - 5} транспортных средств\n"
                                
                            field_value += "```"
                        
                        embed.add_field(
                            name=f"👤 {player_name}",
                            value=field_value,
                            inline=False
                        )

            elif isinstance(player_data, list):
                total_players = len(player_data)
                embed.description = f"Всего игроков онлайн: **{total_players}**"
                
                for i, player in enumerate(player_data):

                    if isinstance(player, dict):
                        player_name = player.get('name', f"Player {i+1}")
                        vehicles = player.get('vehicles', [])
                    else:
                        player_name = player if isinstance(player, str) else f"Player {i+1}"
                        vehicles = []
                    

                    field_value = f"🆔 **ID:** {i+1}\n"
                    

                    if vehicles:
                        vehicle_count = len(vehicles)
                        field_value += f"🚗 **Транспорт:** {vehicle_count} шт.\n"
                        

                        field_value += "```\n"
                        for j, vehicle in enumerate(vehicles[:5], 1):
                            parts = vehicle.split('/')
                            base_vehicle = parts[1] if len(parts) > 1 else vehicle
                            

                            proper_name = car_names.get(base_vehicle, base_vehicle)
                            

                            field_value += f"{j}. {proper_name}\n"

                        if len(vehicles) > 5:
                            field_value += f"...и еще {len(vehicles) - 5} транспортных средств\n"
                            
                        field_value += "```"
                    
                    embed.add_field(
                        name=f"👤 {player_name}",
                        value=field_value,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="ℹ️ Информация",
                    value="Формат данных не распознан. Пожалуйста, проверьте файл players.json.",
                    inline=False
                )
            

            if len(embed.fields) == 0:
                embed.add_field(
                    name="ℹ️ Информация",
                    value="На сервере нет игроков в данный момент.",
                    inline=False
                )
            
            embed.set_footer(text=f"Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
            
            await processing_msg.edit(embed=embed)
            
        except FileNotFoundError:
            await processing_msg.edit(
                embed=disnake.Embed(
                    title="❌ Файл не найден",
                    description=f"Файл players.json не найден по пути: {file_path}",
                    color=disnake.Color.red()
                )
            )
        except json.JSONDecodeError:
            await processing_msg.edit(
                embed=disnake.Embed(
                    title="❌ Ошибка формата",
                    description="Файл players.json содержит некорректный JSON формат.",
                    color=disnake.Color.red()
                )
            )
        except Exception as e:
            print(f"Error parsing player data: {e}")
            await processing_msg.edit(
                embed=disnake.Embed(
                    title="❌ Ошибка обработки данных",
                    description=f"Не удалось обработать данные игроков: {str(e)}",
                    color=disnake.Color.red()
                )
            )
        
    except Exception as e:
        # Handle any errors
        await processing_msg.edit(
            embed=disnake.Embed(
                title="❌ Произошла ошибка",
                description=f"Не удалось получить данные игроков: {str(e)}",
                color=disnake.Color.red()
            )
        )





@bot.slash_command(
    name="сто",
    description="Создать заявку на СТО для вашего автомобиля", guild=1341469479510474813    
)
async def сто(inter: disnake.ApplicationCommandInteraction):
    """Slash command to create a car service request"""
    try:
        # Create modal for car service request
        class CarServiceModal(disnake.ui.Modal):
            def __init__(self):
                components = [
                    disnake.ui.TextInput(
                        label="ID автомобиля",
                        placeholder="Введите ID вашего автомобиля",
                        custom_id="car_id",
                        style=disnake.TextInputStyle.short,
                        required=True
                    ),
                    disnake.ui.TextInput(
                        label="Описание повреждений",
                        placeholder="Опишите повреждения автомобиля (если есть)",
                        custom_id="damage_description",
                        style=disnake.TextInputStyle.paragraph,
                        required=False,
                        max_length=1000
                    )
                ]
                
                super().__init__(
                    title="Заявка на СТО",
                    components=components,
                    custom_id="car_service_modal"
                )
            
            async def callback(self, inter: disnake.ModalInteraction):
                await inter.response.defer(ephemeral=True)
                
                try:
                    car_id = inter.text_values["car_id"]
                    damage_description = inter.text_values["damage_description"] or "Не указано"
                    
                    # Verify car ownership
                    cursor.execute('SELECT brand, model, config FROM purchased_cars WHERE id = ? AND buyer_id = ?', 
                                  (car_id, inter.author.id))
                    car_info = cursor.fetchone()
                    
                    if not car_info:
                        return await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Автомобиль с указанным ID не найден или не принадлежит вам.",
                                color=disnake.Color.red()
                            )
                        )
                    
                    brand, model, config = car_info
                    
                    # Store request in database
                    cursor.execute('''
                        INSERT INTO car_service_requests 
                        (user_id, car_id, brand, model, config, damage_description, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                    ''', (
                        inter.author.id, car_id, brand, model, config, 
                        damage_description, datetime.now().isoformat()
                    ))
                    conn.commit()
                    
                    # Get request ID
                    request_id = cursor.lastrowid
                    
                    # Send instructions to user's DM
                    dm_embed = disnake.Embed(
                        title="📸 Фотографии для СТО",
                        description=(
                            "━━━━━━━━━━ Инструкция ━━━━━━━━━━\n\n"
                            f"Ваша заявка на СТО для автомобиля **{brand} {model}** (ID: {car_id}) принята.\n\n"
                            "Пожалуйста, отправьте **4 фотографии** вашего автомобиля:\n"
                            "1️⃣ Фото спереди\n"
                            "2️⃣ Фото сзади\n"
                            "3️⃣ Фото слева\n"
                            "4️⃣ Фото справа\n\n"
                            f"**Важно:** Отправьте все фотографии в этот личный чат в течение 10 минут.\n"
                            f"**ID заявки:** {request_id}\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.blue()
                    )
                    
                    try:
                        await inter.author.send(embed=dm_embed)
                        
                        # Set up collector for photos
                        def check(m):
                            return m.author.id == inter.author.id and m.guild is None and len(m.attachments) > 0
                        
                        photos = []
                        for i in range(4):
                            try:
                                message = await bot.wait_for('message', check=check, timeout=600)  # 10 minutes timeout
                                photos.append(message.attachments[0].url)
                            except asyncio.TimeoutError:
                                await inter.author.send(
                                    embed=disnake.Embed(
                                        title="⏱️ Время истекло",
                                        description="Вы не отправили все необходимые фотографии в течение отведенного времени. Пожалуйста, создайте новую заявку.",
                                        color=disnake.Color.red()
                                    )
                                )
                                # Update request status to expired
                                cursor.execute('UPDATE car_service_requests SET status = "expired" WHERE id = ?', (request_id,))
                                conn.commit()
                                return
                        
                        # Update request with photo URLs
                        cursor.execute('''
                            UPDATE car_service_requests 
                            SET photo_front = ?, photo_back = ?, photo_left = ?, photo_right = ?, status = "submitted"
                            WHERE id = ?
                        ''', (photos[0], photos[1], photos[2], photos[3], request_id))
                        conn.commit()
                        
                        # Send confirmation to user
                        await inter.author.send(
                            embed=disnake.Embed(
                                title="✅ Фотографии получены",
                                description="Все необходимые фотографии получены. Ваша заявка передана сотрудникам СТО.",
                                color=disnake.Color.green()
                            )
                        )
                        
                        # Create forum post in the service channel
                        service_forum = bot.get_channel(1345079715307716790)  # Replace with actual forum channel ID
                        
                        if service_forum and isinstance(service_forum, disnake.ForumChannel):
                            # Create thread in forum
                            forum_embed = disnake.Embed(
                                title=f"🔧 Заявка СТО #{request_id}",
                                description=(
                                    "━━━━━━━━━━ Информация о заявке ━━━━━━━━━━\n\n"
                                    f"👤 **Клиент:** {inter.author.mention}\n"
                                    f"🚗 **Автомобиль:** {brand} {model} {config}\n"
                                    f"🔢 **ID автомобиля:** {car_id}\n"
                                    f"📝 **Описание повреждений:** {damage_description}\n\n"
                                    "━━━━━━━━━━ Фотографии ━━━━━━━━━━\n\n"
                                ),
                                color=disnake.Color.gold()
                            )
                            
                            # Add photo URLs as fields
                            forum_embed.add_field(name="📸 Фото спереди", value="[Посмотреть](" + photos[0] + ")", inline=True)
                            forum_embed.add_field(name="📸 Фото сзади", value="[Посмотреть](" + photos[1] + ")", inline=True)
                            forum_embed.add_field(name="📸 Фото слева", value="[Посмотреть](" + photos[2] + ")", inline=True)
                            forum_embed.add_field(name="📸 Фото справа", value="[Посмотреть](" + photos[3] + ")", inline=True)
                            
                            # Set first photo as thumbnail
                            forum_embed.set_thumbnail(url=photos[0])
                            
                            # Create thread with tags
                            thread = await service_forum.create_thread(
                                name=f"СТО #{request_id} - {brand} {model}",
                                embed=forum_embed,
                                content=f""  
                            )
                            

                            cursor.execute('UPDATE car_service_requests SET thread_id = ? WHERE id = ?', 
                                          (thread.thread.id, request_id))
                            conn.commit()
                        else:
   
                            print(f"Error: Forum channel not found or is not a forum channel")
                    
                    except disnake.Forbidden:
                        await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Не удалось отправить вам личное сообщение. Пожалуйста, разрешите личные сообщения от участников сервера.",
                                color=disnake.Color.red()
                            )
                        )
                    

                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="✅ Заявка на СТО создана",
                            description=(
                                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                f"🚗 **Автомобиль:** {brand} {model}\n"
                                f"🔢 **ID заявки:** {request_id}\n\n"
                                "📱 **Проверьте личные сообщения** для дальнейших инструкций.\n\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ),
                            color=disnake.Color.green()
                        )
                    )
                    
                except Exception as e:
                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description=f"Произошла ошибка при обработке заявки: {str(e)}",
                            color=disnake.Color.red()
                        )
                    )
        

        await inter.response.send_modal(CarServiceModal())
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при создании заявки на СТО: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)




@bot.slash_command(
    name="тюнинг",
    description="Создать заявку на тюнинг для вашего автомобиля", 
    guild=1341469479510474813    
)
async def тюнинг(inter: disnake.ApplicationCommandInteraction):
    """Slash command to create a car tuning request"""
    try:

        class CarTuningModal(disnake.ui.Modal):
            def __init__(self):
                components = [
                    disnake.ui.TextInput(
                        label="ID автомобиля",
                        placeholder="Введите ID вашего автомобиля",
                        custom_id="car_id",
                        style=disnake.TextInputStyle.short,
                        required=True
                    ),
                    disnake.ui.TextInput(
                        label="Желаемые изменения",
                        placeholder="Опишите какой тюнинг вы хотите сделать",
                        custom_id="tuning_description",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        max_length=1000
                    )
                ]
                
                super().__init__(
                    title="Заявка на тюнинг",
                    components=components,
                    custom_id="car_tuning_modal"
                )
            
            async def callback(self, inter: disnake.ModalInteraction):
                await inter.response.defer(ephemeral=True)
                
                try:
                    car_id = inter.text_values["car_id"]
                    tuning_description = inter.text_values["tuning_description"]
                    

                    cursor.execute('SELECT brand, model, config FROM purchased_cars WHERE id = ? AND buyer_id = ?', 
                                  (car_id, inter.author.id))
                    car_info = cursor.fetchone()
                    
                    if not car_info:
                        return await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Автомобиль с указанным ID не найден или не принадлежит вам.",
                                color=disnake.Color.red()
                            )
                        )
                    
                    brand, model, config = car_info

                    cursor.execute('''
                        INSERT INTO car_tuning_requests 
                        (user_id, car_id, brand, model, config, tuning_description, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                    ''', (
                        inter.author.id, car_id, brand, model, config, 
                        tuning_description, datetime.now().isoformat()
                    ))
                    conn.commit()
                    

                    request_id = cursor.lastrowid

                    dm_embed = disnake.Embed(
                        title="📸 Фотографии для тюнинг ателье",
                        description=(
                            "━━━━━━━━━━ Инструкция ━━━━━━━━━━\n\n"
                            f"Ваша заявка на тюнинг для автомобиля **{brand} {model}** (ID: {car_id}) принята.\n\n"
                            "Пожалуйста, отправьте **4 фотографии** вашего автомобиля:\n"
                            "1️⃣ Фото спереди\n"
                            "2️⃣ Фото сзади\n"
                            "3️⃣ Фото слева\n"
                            "4️⃣ Фото справа\n\n"
                            f"**Важно:** Отправьте все фотографии в этот личный чат в течение 10 минут.\n"
                            f"**ID заявки:** {request_id}\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.blue()
                    )
                    
                    try:
                        await inter.author.send(embed=dm_embed)
                        

                        def check(m):
                            return m.author.id == inter.author.id and m.guild is None and len(m.attachments) > 0
                        
                        photos = []
                        for i in range(4):
                            try:
                                message = await bot.wait_for('message', check=check, timeout=600)  
                                photos.append(message.attachments[0].url)
                            except asyncio.TimeoutError:
                                await inter.author.send(
                                    embed=disnake.Embed(
                                        title="⏱️ Время истекло",
                                        description="Вы не отправили все необходимые фотографии в течение отведенного времени. Пожалуйста, создайте новую заявку.",
                                        color=disnake.Color.red()
                                    )
                                )

                                cursor.execute('UPDATE car_tuning_requests SET status = "expired" WHERE id = ?', (request_id,))
                                conn.commit()
                                return
                        

                        cursor.execute('''
                            UPDATE car_tuning_requests 
                            SET photo_front = ?, photo_back = ?, photo_left = ?, photo_right = ?, status = "submitted"
                            WHERE id = ?
                        ''', (photos[0], photos[1], photos[2], photos[3], request_id))
                        conn.commit()
                        

                        await inter.author.send(
                            embed=disnake.Embed(
                                title="✅ Фотографии получены",
                                description="Все необходимые фотографии получены. Ваша заявка передана сотрудникам тюнинг ателье.",
                                color=disnake.Color.green()
                            )
                        )
                        

                        tuning_forum = bot.get_channel(1345143292504834059)  
                        
                        if tuning_forum and isinstance(tuning_forum, disnake.ForumChannel):
                            # Create thread in forum
                            forum_embed = disnake.Embed(
                                title=f"🔧 Заявка на тюнинг #{request_id}",
                                description=(
                                    "━━━━━━━━━━ Информация о заявке ━━━━━━━━━━\n\n"
                                    f"👤 **Клиент:** {inter.author.mention}\n"
                                    f"🚗 **Автомобиль:** {brand} {model} {config}\n"
                                    f"🔢 **ID автомобиля:** {car_id}\n"
                                    f"📝 **Желаемые изменения:** {tuning_description}\n\n"
                                    "━━━━━━━━━━ Фотографии ━━━━━━━━━━\n\n"
                                ),
                                color=disnake.Color.purple()
                            )
                            

                            forum_embed.add_field(name="📸 Фото спереди", value="[Посмотреть](" + photos[0] + ")", inline=True)
                            forum_embed.add_field(name="📸 Фото сзади", value="[Посмотреть](" + photos[1] + ")", inline=True)
                            forum_embed.add_field(name="📸 Фото слева", value="[Посмотреть](" + photos[2] + ")", inline=True)
                            forum_embed.add_field(name="📸 Фото справа", value="[Посмотреть](" + photos[3] + ")", inline=True)
                            
     
                            forum_embed.set_thumbnail(url=photos[0])
                            
        
                            thread = await tuning_forum.create_thread(
                                name=f"Тюнинг #{request_id} - {brand} {model}",
                                embed=forum_embed,
                                content=f""  
                            )
                            

                            cursor.execute('UPDATE car_tuning_requests SET thread_id = ? WHERE id = ?', 
                                          (thread.thread.id, request_id))
                            conn.commit()
                        else:
                            print(f"Error: Forum channel not found or is not a forum channel")
                    
                    except disnake.Forbidden:
                        await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Не удалось отправить вам личное сообщение. Пожалуйста, разрешите личные сообщения от участников сервера.",
                                color=disnake.Color.red()
                            )
                        )
                    
                    # Send confirmation to channel
                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="✅ Заявка на тюнинг создана",
                            description=(
                                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                f"🚗 **Автомобиль:** {brand} {model}\n"
                                f"🔢 **ID заявки:** {request_id}\n\n"
                                "📱 **Проверьте личные сообщения** для дальнейших инструкций.\n\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ),
                            color=disnake.Color.green()
                        )
                    )
                    
                except Exception as e:
                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description=f"Произошла ошибка при обработке заявки: {str(e)}",
                            color=disnake.Color.red()
                        )
                    )
        

        await inter.response.send_modal(CarTuningModal())
        
    except Exception as e:
        await inter.response.send_message(
            embed=disnake.Embed(
                title="❌ Ошибка",
                description=f"Произошла ошибка при создании заявки на тюнинг: {str(e)}",
                color=disnake.Color.red()
            ),
            ephemeral=True
        )



@bot.slash_command(
    name="шиномонтаж",
    description="Создать заявку на шиномонтаж для вашего автомобиля", 
    guild=1341469479510474813    
)
async def шиномонтаж(inter: disnake.ApplicationCommandInteraction):
    """Slash command to create a tire service request"""
    try:
        # Create modal for tire service request
        class TireServiceModal(disnake.ui.Modal):
            def __init__(self):
                components = [
                    disnake.ui.TextInput(
                        label="ID автомобиля",
                        placeholder="Введите ID вашего автомобиля",
                        custom_id="car_id",
                        style=disnake.TextInputStyle.short,
                        required=True
                    ),
                    disnake.ui.TextInput(
                        label="Тип услуги",
                        placeholder="Например: замена шин, балансировка, ремонт",
                        custom_id="service_type",
                        style=disnake.TextInputStyle.short,
                        required=True
                    ),
                    disnake.ui.TextInput(
                        label="Описание",
                        placeholder="Опишите подробнее что нужно сделать",
                        custom_id="service_description",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        max_length=1000
                    )
                ]
                
                super().__init__(
                    title="Заявка на шиномонтаж",
                    components=components,
                    custom_id="tire_service_modal"
                )
            
            async def callback(self, inter: disnake.ModalInteraction):
                await inter.response.defer(ephemeral=True)
                
                try:
                    car_id = inter.text_values["car_id"]
                    service_type = inter.text_values["service_type"]
                    service_description = inter.text_values["service_description"]
                    

                    cursor.execute('SELECT brand, model, config FROM purchased_cars WHERE id = ? AND buyer_id = ?', 
                                  (car_id, inter.author.id))
                    car_info = cursor.fetchone()
                    
                    if not car_info:
                        return await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Автомобиль с указанным ID не найден или не принадлежит вам.",
                                color=disnake.Color.red()
                            )
                        )
                    
                    brand, model, config = car_info
                    

                    cursor.execute('''
                        INSERT INTO tire_service_requests 
                        (user_id, car_id, brand, model, config, service_type, service_description, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                    ''', (
                        inter.author.id, car_id, brand, model, config, 
                        service_type, service_description, datetime.now().isoformat()
                    ))
                    conn.commit()
                    
                    # Get request ID
                    request_id = cursor.lastrowid
                    

                    dm_embed = disnake.Embed(
                        title="📸 Фотографии для шиномонтажа",
                        description=(
                            "━━━━━━━━━━ Инструкция ━━━━━━━━━━\n\n"
                            f"Ваша заявка на шиномонтаж для автомобиля **{brand} {model}** (ID: {car_id}) принята.\n\n"
                            "Пожалуйста, отправьте **2 фотографии**:\n"
                            "1️⃣ Фото дисков\n"
                            "2️⃣ Фото шин\n\n"
                            f"**Важно:** Отправьте все фотографии в этот личный чат в течение 10 минут.\n"
                            f"**ID заявки:** {request_id}\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.blue()
                    )
                    
                    try:
                        await inter.author.send(embed=dm_embed)
                        

                        def check(m):
                            return m.author.id == inter.author.id and m.guild is None and len(m.attachments) > 0
                        
                        photos = []
                        for i in range(2): 
                            try:
                                message = await bot.wait_for('message', check=check, timeout=600)  
                                photos.append(message.attachments[0].url)
                            except asyncio.TimeoutError:
                                await inter.author.send(
                                    embed=disnake.Embed(
                                        title="⏱️ Время истекло",
                                        description="Вы не отправили все необходимые фотографии в течение отведенного времени. Пожалуйста, создайте новую заявку.",
                                        color=disnake.Color.red()
                                    )
                                )

                                cursor.execute('UPDATE tire_service_requests SET status = "expired" WHERE id = ?', (request_id,))
                                conn.commit()
                                return
                        

                        cursor.execute('''
                            UPDATE tire_service_requests 
                            SET photo_wheels = ?, photo_tires = ?, status = "submitted"
                            WHERE id = ?
                        ''', (photos[0], photos[1], request_id))
                        conn.commit()

                        await inter.author.send(
                            embed=disnake.Embed(
                                title="✅ Фотографии получены",
                                description="Все необходимые фотографии получены. Ваша заявка передана сотрудникам шиномонтажа.",
                                color=disnake.Color.green()
                            )
                        )
                        

                        tire_forum = bot.get_channel(1345075265159696394)  
                        
                        if tire_forum and isinstance(tire_forum, disnake.ForumChannel):
                            # Create thread in forum
                            forum_embed = disnake.Embed(
                                title=f"🔧 Заявка на шиномонтаж #{request_id}",
                                description=(
                                    "━━━━━━━━━━ Информация о заявке ━━━━━━━━━━\n\n"
                                    f"👤 **Клиент:** {inter.author.mention}\n"
                                    f"🚗 **Автомобиль:** {brand} {model} {config}\n"
                                    f"🔢 **ID автомобиля:** {car_id}\n"
                                    f"🔧 **Тип услуги:** {service_type}\n"
                                    f"📝 **Описание:** {service_description}\n\n"
                                    "━━━━━━━━━━ Фотографии ━━━━━━━━━━\n\n"
                                ),
                                color=disnake.Color.orange()
                            )
                            
                            # Add photo URLs as fields
                            forum_embed.add_field(name="📸 Фото дисков", value="[Посмотреть](" + photos[0] + ")", inline=True)
                            forum_embed.add_field(name="📸 Фото шин", value="[Посмотреть](" + photos[1] + ")", inline=True)
                            
                            # Set first photo as thumbnail
                            forum_embed.set_thumbnail(url=photos[0])
                            
                            # Create thread with tags
                            thread = await tire_forum.create_thread(
                                name=f"Шиномонтаж #{request_id} - {brand} {model}",
                                embed=forum_embed,
                                content=f""  
                            )
                            

                            cursor.execute('UPDATE tire_service_requests SET thread_id = ? WHERE id = ?', 
                                          (thread.thread.id, request_id))
                            conn.commit()
                        else:
                            print(f"Error: Forum channel not found or is not a forum channel")
                    
                    except disnake.Forbidden:
                        await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Не удалось отправить вам личное сообщение. Пожалуйста, разрешите личные сообщения от участников сервера.",
                                color=disnake.Color.red()
                            )
                        )
                    
                    # Send confirmation to channel
                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="✅ Заявка на шиномонтаж создана",
                            description=(
                                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                f"🚗 **Автомобиль:** {brand} {model}\n"
                                f"🔢 **ID заявки:** {request_id}\n\n"
                                "📱 **Проверьте личные сообщения** для дальнейших инструкций.\n\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ),
                            color=disnake.Color.green()
                        )
                    )
                    
                except Exception as e:
                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description=f"Произошла ошибка при обработке заявки: {str(e)}",
                            color=disnake.Color.red()
                        )
                    )
        
        # Send the modal
        await inter.response.send_modal(TireServiceModal())
        
    except Exception as e:
        # Handle any errors
        await inter.response.send_message(
            embed=disnake.Embed(
                title="❌ Ошибка",
                description=f"Произошла ошибка при создании заявки на шиномонтаж: {str(e)}",
                color=disnake.Color.red()
            ),
            ephemeral=True
        )




@bot.slash_command(
    name="выставить_счёт",
    description="Выставить счёт за услуги",
    guild_ids=[1341469479510474813]
)
@commands.has_any_role("Работник СТО", "Работник Тюнинг Ателье", "Работник Шиномонтажки")
async def выставить_счёт(inter: disnake.ApplicationCommandInteraction):
    """Slash command to issue an invoice for services"""
    
    # Create modal for invoice creation
    class InvoiceModal(disnake.ui.Modal):
        def __init__(self):
            components = [
                disnake.ui.TextInput(
                    label="Тип услуги",
                    placeholder="сто, ателье или шиномонтаж",
                    custom_id="service_type",
                    style=disnake.TextInputStyle.short,
                    required=True
                ),
                disnake.ui.TextInput(
                    label="ID заявки",
                    placeholder="Введите ID заявки",
                    custom_id="request_id",
                    style=disnake.TextInputStyle.short,
                    required=True
                ),
                disnake.ui.TextInput(
                    label="Сумма",
                    placeholder="Введите сумму в ₽",
                    custom_id="amount",
                    style=disnake.TextInputStyle.short,
                    required=True
                )
            ]
            
            super().__init__(
                title="Выставление счёта",
                components=components,
                custom_id="invoice_modal"
            )
        
        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.defer(ephemeral=True)
            
            try:
                service_type = inter.text_values["service_type"].lower()
                request_id = int(inter.text_values["request_id"])
                amount = int(inter.text_values["amount"])
                
                if amount < 1:
                    return await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description="Сумма должна быть положительным числом.",
                            color=disnake.Color.red()
                        )
                    )
                    
                valid_services = {
                    "сто": "car_service_requests",
                    "ателье": "car_tuning_requests",
                    "шиномонтаж": "tire_service_requests"
                }
                
                # Map roles to allowed service types
                role_service_map = {
                    "Работник СТО": ["сто"],
                    "Работник Тюнинг Ателье": ["ателье"],
                    "Работник Шиномонтажки": ["шиномонтаж"]
                }
                
                # Check if user has permission for the requested service type
                has_permission = False
                for role in inter.author.roles:
                    if role.name in role_service_map and service_type in role_service_map[role.name]:
                        has_permission = True
                        break
                
                if not has_permission:
                    return await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Доступ запрещен",
                            description=f"У вас нет прав для выставления счетов за услуги типа '{service_type}'",
                            color=disnake.Color.red()
                        )
                    )
                
                if service_type not in valid_services:
                    return await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description="Неверный тип услуги. Используйте: сто, ателье или шиномонтаж",
                            color=disnake.Color.red()
                        )
                    )
                
                # Get the table name for the service type
                table_name = valid_services[service_type]
                
                # Check if request exists and get user_id
                cursor.execute(f'SELECT user_id, brand, model, thread_id FROM {table_name} WHERE id = ?', (request_id,))
                request_info = cursor.fetchone()
                
                if not request_info:
                    return await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description=f"Заявка #{request_id} не найдена для указанного типа услуги",
                            color=disnake.Color.red()
                        )
                    )
                
                user_id, brand, model, thread_id = request_info
                

                try:
                    user = await bot.fetch_user(user_id)
                except disnake.NotFound:
                    return await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description="Не удалось найти пользователя, связанного с этой заявкой",
                            color=disnake.Color.red()
                        )
                    )
                

                service_names = {
                    "сто": "СТО",
                    "ателье": "Тюнинг Ателье",
                    "шиномонтаж": "Шиномонтаж"
                }
                
                invoice_embed = disnake.Embed(
                    title=f"💰 Счёт за услуги {service_names[service_type]}",
                    description=(
                        "━━━━━━━━━━ Информация о счёте ━━━━━━━━━━\n\n"
                        f"🚗 **Автомобиль:** {brand} {model}\n"
                        f"🔢 **ID заявки:** {request_id}\n"
                        f"💵 **Сумма к оплате:** {amount}₽\n\n"
                        "Для оплаты используйте команду:\n"
                        f"`/оплатить_счёт {service_type} {request_id}`\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.gold()
                )
                
                invoice_embed.set_footer(text=f"Счёт выставлен: {inter.author.display_name}")
                invoice_embed.timestamp = datetime.now()

                try:
                    await user.send(embed=invoice_embed)
                except disnake.Forbidden:
                    return await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description="Не удалось отправить счёт пользователю. Возможно, у него отключены личные сообщения.",
                            color=disnake.Color.red()
                        )
                    )

                # Store invoice in database
                cursor.execute('''
                    INSERT INTO service_invoices 
                    (service_type, request_id, user_id, amount, issued_by, issued_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    service_type, request_id, user_id, amount, 
                    inter.author.id, datetime.now().isoformat()
                ))
                conn.commit()
                
                # Get invoice ID
                invoice_id = cursor.lastrowid
                
                # Send confirmation
                confirm_embed = disnake.Embed(
                    title="✅ Счёт выставлен",
                    description=(
                        "━━━━━━━━━━ Информация о счёте ━━━━━━━━━━\n\n"
                        f"💰 **Сумма:** {amount:,}₽\n"
                        f"👤 **Клиент:** {user.mention}\n"
                        f"🔢 **ID счёта:** {invoice_id}\n"
                        f"🔧 **Тип услуги:** {service_names[service_type]}\n"
                        f"📝 **ID заявки:** {request_id}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=disnake.Color.green()
                )
                await inter.edit_original_response(embed=confirm_embed)
                
                # If thread_id exists, post in the thread
                if thread_id:
                    try:
                        thread = await bot.fetch_channel(thread_id)
                        thread_embed = disnake.Embed(
                            title="💰 Выставлен счёт",
                            description=(
                                "━━━━━━━━━━ Информация о счёте ━━━━━━━━━━\n\n"
                                f"👤 **Клиент:** {user.mention}\n"
                                f"💵 **Сумма:** {amount:,}₽\n"
                                f"🔢 **ID счёта:** {invoice_id}\n\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ),
                            color=disnake.Color.gold()
                        )
                        thread_embed.set_footer(text=f"Выставил: {inter.author.display_name}")
                        await thread.send(embed=thread_embed)
                    except Exception as e:
                        print(f"Error posting to thread: {e}")
                
            except ValueError:
                await inter.edit_original_response(
                    embed=disnake.Embed(
                        title="❌ Ошибка",
                        description="ID заявки и сумма должны быть числами",
                        color=disnake.Color.red()
                    )
                )
            except Exception as e:
                await inter.edit_original_response(
                    embed=disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Произошла ошибка при выставлении счёта: {str(e)}",
                        color=disnake.Color.red()
                    )
                )
    
    # Send the modal
    await inter.response.send_modal(InvoiceModal())

@bot.slash_command(
    name="оплатить_счёт",
    description="Оплатить счёт за услуги",
    guild_ids=[1341469479510474813]
)
async def pay_invoice(inter: disnake.ApplicationCommandInteraction):
    """Группа команд для оплаты счетов за различные услуги"""
    pass

@pay_invoice.sub_command(
    name="сто",
    description="Оплатить счёт за услуги СТО"
)
async def pay_car_service(
    inter: disnake.ApplicationCommandInteraction,
    request_id: int = commands.Param(description="ID заявки")
):
    """Оплатить счёт за услуги СТО"""
    await process_invoice_payment(inter, "сто", request_id)

@pay_invoice.sub_command(
    name="ателье",
    description="Оплатить счёт за услуги тюнинг ателье"
)
async def pay_tuning_service(
    inter: disnake.ApplicationCommandInteraction,
    request_id: int = commands.Param(description="ID заявки")
):
    """Оплатить счёт за услуги тюнинг ателье"""
    await process_invoice_payment(inter, "ателье", request_id)

@pay_invoice.sub_command(
    name="шиномонтаж",
    description="Оплатить счёт за услуги шиномонтажа"
)
async def pay_tire_service(
    inter: disnake.ApplicationCommandInteraction,
    request_id: int = commands.Param(description="ID заявки")
):
    """Оплатить счёт за услуги шиномонтажа"""
    await process_invoice_payment(inter, "шиномонтаж", request_id)

# Helper function to process payments for all service types
async def process_invoice_payment(inter: disnake.ApplicationCommandInteraction, service_type: str, request_id: int):
    """Process payment for a service invoice"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Validate service type and get table name
        valid_services = {
            "сто": "car_service_requests",
            "ателье": "car_tuning_requests",
            "шиномонтаж": "tire_service_requests"
        }
        
        table_name = valid_services[service_type]
        
        # Check if invoice exists
        cursor.execute('''
            SELECT id, amount, status, user_id 
            FROM service_invoices 
            WHERE service_type = ? AND request_id = ? AND status = 'pending'
        ''', (service_type, request_id))
        
        invoice = cursor.fetchone()
        
        if not invoice:
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Ошибка",
                    description="Счёт не найден или уже оплачен",
                    color=disnake.Color.red()
                )
            )
        
        invoice_id, amount, status, user_id = invoice
        
        # Verify user is the invoice owner
        if int(user_id) != inter.author.id:
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Ошибка",
                    description="Этот счёт выставлен другому пользователю",
                    color=disnake.Color.red()
                )
            )
        
        # Check user balance
        bal = unbclient.get_user_bal(1341469479510474813, inter.author.id)
        if bal['cash'] < amount:
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Недостаточно средств",
                    description=f"Для оплаты счёта требуется {amount}₽. У вас на счету {bal['cash']}₽",
                    color=disnake.Color.red()
                )
            )
        
        # Process payment
        new_balance = bal['cash'] - amount
        unbclient.set_user_bal(1341469479510474813, inter.author.id, cash=new_balance)
        
        # Update invoice status
        cursor.execute('''
            UPDATE service_invoices 
            SET status = 'paid', paid_at = ? 
            WHERE id = ?
        ''', (datetime.now().isoformat(), invoice_id))
        
        # Update request status
        cursor.execute(f'''
            UPDATE {table_name}
            SET status = 'paid'
            WHERE id = ?
        ''', (request_id,))
        
        conn.commit()
        
        # Send confirmation to user
        payment_embed = disnake.Embed(
            title="✅ Оплата успешна",
            description=(
                "━━━━━━━━━━ Информация о платеже ━━━━━━━━━━\n\n"
                f"💰 **Сумма:** {amount}₽\n"
                f"🧾 **ID счёта:** {invoice_id}\n"
                f"🔢 **ID заявки:** {request_id}\n"
                f"💵 **Остаток на счету:** {new_balance}₽\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        payment_embed.timestamp = datetime.now()
        await inter.edit_original_response(embed=payment_embed)
        
        # Get thread_id to notify in the thread
        cursor.execute(f'SELECT thread_id FROM {table_name} WHERE id = ?', (request_id,))
        thread_result = cursor.fetchone()
        
        if thread_result and thread_result[0]:
            try:
                thread = await bot.fetch_channel(thread_result[0])
                thread_embed = disnake.Embed(
                    title="💵 Счёт оплачен",
                    description=(
                        f"Клиент {inter.author.mention} оплатил счёт на сумму **{amount}₽**\n"
                        f"**ID счёта:** {invoice_id}"
                    ),
                    color=disnake.Color.green()
                )
                await thread.send(embed=thread_embed)
            except Exception as e:
                print(f"Error posting to thread: {e}")
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при оплате счёта: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)



@bot.slash_command(
    name="выписать_протокол",
    description="Выписать протокол о нарушении ПДД",
    guild_ids=[1341469479510474813]
)
@commands.has_role("ГИБДД")
async def выписать_протокол(inter: disnake.ApplicationCommandInteraction):
    """Slash command to issue a traffic violation protocol"""
    
    # Create modal for protocol creation
    class TrafficViolationModal(disnake.ui.Modal):
        def __init__(self):
            components = [
                disnake.ui.TextInput(
                    label="Имя и фамилия нарушителя",
                    placeholder="Введите отображаемый ник нарушителя в Discord",
                    custom_id="violator_name",
                    style=disnake.TextInputStyle.short,
                    required=True
                ),
                disnake.ui.TextInput(
                    label="Детали нарушения",
                    placeholder="Укажите статьи ПДД и подробное описание ситуации",
                    custom_id="violation_details",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    max_length=1000
                ),
                disnake.ui.TextInput(
                    label="Сумма штрафа (₽)",
                    placeholder="Введите сумму штрафа в рублях",
                    custom_id="fine_amount",
                    style=disnake.TextInputStyle.short,
                    required=True
                ),
                disnake.ui.TextInput(
                    label="ID машины на штрафстоянке (если есть)",
                    placeholder="Оставьте пустым, если машина не на штрафстоянке",
                    custom_id="impounded_car_id",
                    style=disnake.TextInputStyle.short,
                    required=False
                ),
                disnake.ui.TextInput(
                    label="Лишать прав? (Да/Нет)",
                    placeholder="Введите 'Да' или 'Нет'",
                    custom_id="revoke_license",
                    style=disnake.TextInputStyle.short,
                    required=True
                )
            ]
            
            super().__init__(
                title="Протокол о нарушении ПДД",
                components=components,
                custom_id="traffic_violation_modal"
            )
        
        async def callback(self, inter: disnake.ModalInteraction):
            await inter.response.defer(ephemeral=True)
            
            try:
                violator_name = inter.text_values["violator_name"]
                violation_details = inter.text_values["violation_details"]
                fine_amount = inter.text_values["fine_amount"]
                impounded_car_id = inter.text_values["impounded_car_id"]
                revoke_license = inter.text_values["revoke_license"].lower() == "да"
                
                # Validate fine amount
                try:
                    fine_amount = int(fine_amount)
                    if fine_amount < 0:
                        raise ValueError("Сумма штрафа не может быть отрицательной")
                except ValueError:
                    return await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description="Сумма штрафа должна быть положительным числом.",
                            color=disnake.Color.red()
                        )
                    )
                

                violator = None
                guild = inter.guild
                
                for member in guild.members:
                    if member.display_name.lower() == violator_name.lower():
                        violator = member
                        break
                    
                    if '[' in member.display_name:
                        name_part = member.display_name.split('[')[0].strip().lower()
                        if name_part == violator_name.lower():
                            violator = member
                            break
                
                if not violator:
                    return await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description=f"Пользователь с именем '{violator_name}' не найден на сервере.",
                            color=disnake.Color.red()
                        )
                    )
                
                cursor.execute('SELECT MAX(id) FROM traffic_violations')
                result = cursor.fetchone()
                protocol_id = 1 if result[0] is None else result[0] + 1
                
                cursor.execute('''
                    INSERT INTO traffic_violations 
                    (id, violator_id, officer_id, violation_details, 
                     impounded_car_id, license_revoked, fine_amount, issued_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    protocol_id, violator.id, inter.author.id, violation_details, 
                    impounded_car_id if impounded_car_id else None, 
                    revoke_license, fine_amount, datetime.now().isoformat()
                ))
                conn.commit()
                
                # Create protocol embed
                protocol_embed = disnake.Embed(
                    title=f"🚨 Протокол о нарушении ПДД #{protocol_id}",
                    description=(
                        "━━━━━━━━━━ Информация о нарушении ━━━━━━━━━━\n\n"
                        f"👤 **Нарушитель:** {violator.mention}\n"
                        f"👮 **Сотрудник:** {inter.author.mention}\n"
                        f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                        f"💰 **Штраф:** {fine_amount:,}₽\n\n"
                        f"📄 **Детали нарушения:**\n{violation_details}\n\n"
                    ),
                    color=disnake.Color.red()
                )
                
                if impounded_car_id:
                    cursor.execute('SELECT brand, model, config FROM purchased_cars WHERE id = ?', (impounded_car_id,))
                    car_info = cursor.fetchone()
                    
                    if car_info:
                        brand, model, config = car_info
                        protocol_embed.add_field(
                            name="🚗 Автомобиль на штрафстоянке",
                            value=f"**ID:** {impounded_car_id}\n**Марка:** {brand}\n**Модель:** {model}\n**Комплектация:** {config}",
                            inline=False
                        )
                    else:
                        protocol_embed.add_field(
                            name="🚗 Автомобиль на штрафстоянке",
                            value=f"**ID:** {impounded_car_id}\n**Примечание:** Автомобиль не найден в базе данных",
                            inline=False
                        )
                
                if revoke_license:
                    protocol_embed.add_field(
                        name="🚫 Водительское удостоверение",
                        value="**Статус:** Изъято",
                        inline=False
                    )
                    
                    cursor.execute('UPDATE licenses SET status = "revoked" WHERE user_id = ?', (str(violator.id),))
                    conn.commit()
                protocol_embed.add_field(
                    name="⚙️ Доступные команды",
                    value=(
                        "**!оплатить_штраф** - оплатить штраф\n"
                        "**/апелляция** - подать апелляцию в суд"
                    ),
                    inline=False
                )
                

                violations_forum = bot.get_channel(1346440724903759904)  
                
                if violations_forum and isinstance(violations_forum, disnake.ForumChannel):
                    thread = await violations_forum.create_thread(
                        name=f"Протокол #{protocol_id} - {violator.display_name}",
                        embed=protocol_embed,
                        content=f"" 
                    )
                    
                    cursor.execute('UPDATE traffic_violations SET thread_id = ? WHERE id = ?', 
                                  (thread.thread.id, protocol_id))
                    conn.commit()
                else:

                    print(f"Error: Forum channel not found or is not a forum channel")
                

                try:
                    dm_embed = disnake.Embed(
                        title="🚨 Вам выписан протокол о нарушении ПДД",
                        description=(
                            "━━━━━━━━━━ Информация о нарушении ━━━━━━━━━━\n\n"
                            f"👮 **Сотрудник:** {inter.author.mention}\n"
                            f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                            f"💰 **Штраф:** {fine_amount:,}₽\n\n"
                            f"📄 **Детали нарушения:**\n{violation_details}\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.red()
                    )
                    

                    if impounded_car_id and car_info:
                        dm_embed.add_field(
                            name="🚗 Автомобиль на штрафстоянке",
                            value=f"**ID:** {impounded_car_id}\n**Марка:** {brand}\n**Модель:** {model}\n**Комплектация:** {config}",
                            inline=False
                        )
                    

                    if revoke_license:
                        dm_embed.add_field(
                            name="🚫 Водительское удостоверение",
                            value="**Статус:** Изъято\nВам необходимо пересдать экзамен для получения нового удостоверения.",
                            inline=False
                        )
                    

                    dm_embed.add_field(
                        name="💳 Оплата штрафа",
                        value="Для оплаты штрафа используйте команду `!оплатить_штраф` в канале протоколов!",
                        inline=False
                    )
                    
                    await violator.send(embed=dm_embed)
                except disnake.Forbidden:
                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="⚠️ Предупреждение",
                            description=f"Протокол создан, но не удалось отправить уведомление нарушителю. Возможно, у него отключены личные сообщения.",
                            color=disnake.Color.orange()
                        )
                    )

                await inter.edit_original_response(
                    embed=disnake.Embed(
                        title="✅ Протокол выписан",
                        description=(
                            "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                            f"🔢 **ID протокола:** {protocol_id}\n"
                            f"👤 **Нарушитель:** {violator.mention}\n"
                            f"💰 **Штраф:** {fine_amount:,}₽\n\n"
                            "Протокол успешно создан и отправлен нарушителю.\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.green()
                    )
                )
                
            except Exception as e:
                await inter.edit_original_response(
                    embed=disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Произошла ошибка при создании протокола: {str(e)}",
                        color=disnake.Color.red()
                    )
                )
    

    await inter.response.send_modal(TrafficViolationModal())


@bot.slash_command(
    name="оплатить_штраф",
    description="Оплатить штраф за нарушение ПДД",
    guild_ids=[1341469479510474813]
)
async def pay_fine_slash(inter: disnake.ApplicationCommandInteraction):
    """Slash command to pay a traffic violation fine"""
    try:
        await inter.response.defer(ephemeral=True)
        
        # Check if the command is used in a thread
        if not isinstance(inter.channel, disnake.Thread):
            return await inter.edit_original_response(content="❌ Эта команда может использоваться только в треде с протоколом о нарушении.")
        
        # Get the thread ID
        thread_id = inter.channel.id
        
        # Find the violation by thread ID
        cursor.execute('''
            SELECT id, violator_id, fine_amount, status
            FROM traffic_violations
            WHERE thread_id = ?
        ''', (thread_id,))
        
        violation = cursor.fetchone()
        
        if not violation:
            return await inter.edit_original_response(content="❌ Протокол о нарушении не найден для этого треда.")
        
        protocol_id, violator_id, fine_amount, status = violation
        
        # Check if the user is the violator
        if inter.author.id != violator_id:
            return await inter.edit_original_response(content="❌ Только нарушитель может оплатить этот штраф.")
        
        # Check if the fine is already paid
        if status != "active":
            return await inter.edit_original_response(content="ℹ️ Этот штраф уже оплачен или аннулирован.")
        
        # Check if the user has enough money
        user_balance = unbclient.get_user_bal(1341469479510474813, inter.author.id)
        if user_balance['cash'] < fine_amount:
            return await inter.edit_original_response(content=f"❌ У вас недостаточно средств для оплаты штрафа. Необходимо: {fine_amount:,}₽")
        
        # Process payment
        # Deduct money from user
        new_balance = user_balance['cash'] - fine_amount
        unbclient.set_user_bal(1341469479510474813, inter.author.id, cash=new_balance)
        
        # Update violation status
        cursor.execute('''
            UPDATE traffic_violations
            SET status = 'paid'
            WHERE id = ?
        ''', (protocol_id,))
        conn.commit()

        # Create a payment confirmation embed for the thread
        thread_embed = disnake.Embed(
            title="💰 Штраф оплачен",
            description=(
                f"Протокол №{protocol_id} был оплачен {inter.author.mention}.\n"
                f"Сумма: {fine_amount:,}₽\n"
                f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            color=disnake.Color.green()
        )
        await inter.channel.send(embed=thread_embed)
        
        # Send confirmation to user
        success_embed = disnake.Embed(
            title="✅ Штраф оплачен",
            description=(
                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                f"🔢 **ID протокола:** {protocol_id}\n"
                f"💰 **Сумма штрафа:** {fine_amount:,}₽\n"
                f"💵 **Остаток на счету:** {new_balance:,}₽\n\n"
                "Штраф успешно оплачен. Спасибо за своевременную оплату!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        await inter.edit_original_response(embed=success_embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при оплате штрафа: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.edit_original_response(embed=error_embed)


@bot.slash_command(
    name="апелляция",
    description="Подать апелляцию на штраф",
    guild_ids=[1341469479510474813]
)
async def appeal_slash(inter: disnake.ApplicationCommandInteraction):
    """Slash command to appeal a traffic violation fine"""
    try:
        # Check if the command is used in a thread
        if not isinstance(inter.channel, disnake.Thread):
            return await inter.response.send_message("❌ Эта команда может использоваться только в треде с протоколом о нарушении.", ephemeral=True)
        
        # Get the thread ID
        thread_id = inter.channel.id
        
        # Find the violation by thread ID
        cursor.execute('''
            SELECT id, violator_id, officer_id, fine_amount, status
            FROM traffic_violations
            WHERE thread_id = ?
        ''', (thread_id,))
        
        violation = cursor.fetchone()
        
        if not violation:
            return await inter.response.send_message("❌ Протокол о нарушении не найден для этого треда.", ephemeral=True)
        
        protocol_id, violator_id, officer_id, fine_amount, status = violation
        
        # Check if the user is the violator
        if inter.author.id != violator_id:
            return await inter.response.send_message("❌ Только нарушитель может подать апелляцию на этот штраф.", ephemeral=True)
        
        # Check if the fine is already paid
        if status != "active":
            return await inter.response.send_message("ℹ️ Этот штраф уже оплачен или аннулирован, апелляция невозможна.", ephemeral=True)
        
        # Get officer information
        officer = await bot.fetch_user(officer_id)
        officer_name = officer.display_name if officer else "Неизвестный сотрудник"
        
        # Create modal for appeal
        class AppealModal(disnake.ui.Modal):
            def __init__(self):
                components = [
                    disnake.ui.TextInput(
                        label="Суть дела",
                        placeholder="Кратко изложите суть вашего дела. Укажите, что произошло, когда и где.",
                        custom_id="case_details",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        max_length=1000
                    ),
                    disnake.ui.TextInput(
                        label="Требования",
                        placeholder="Четко сформулируйте ваши требования к суду.",
                        custom_id="demands",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        max_length=500
                    ),
                    disnake.ui.TextInput(
                        label="Доказательства",
                        placeholder="Перечислите документы и другие доказательства.",
                        custom_id="evidence",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        max_length=500
                    ),
                    disnake.ui.TextInput(
                        label="Дополнительные сведения",
                        placeholder="Если есть какие-либо дополнительные сведения, укажите их здесь.",
                        custom_id="additional_info",
                        style=disnake.TextInputStyle.paragraph,
                        required=False,
                        max_length=500
                    )
                ]
                
                super().__init__(
                    title="Апелляция на штраф",
                    components=components,
                    custom_id="appeal_modal"
                )
            
            async def callback(self, inter: disnake.ModalInteraction):
                await inter.response.defer(ephemeral=True)
                
                try:
                    case_details = inter.text_values["case_details"]
                    demands = inter.text_values["demands"]
                    evidence = inter.text_values["evidence"]
                    additional_info = inter.text_values["additional_info"]
                    
                    # Format the appeal template
                    appeal_template = (
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "📜 **ГОРОДСКОЙ СУД ГОРОДА МАКСИТАУН**\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        "🏛️ **Адрес суда:**\n"
                        "   ул. Коммунарная д.4\n"
                        "   г.Макситаун, Брянская обл., 240010\n\n"
                        "━━━━━━━━━━ Информация о сторонах ━━━━━━━━━━\n\n"
                        f"👤 **Заявитель:**\n"
                        f"   {inter.author.mention}\n\n"
                        f"⚖️ **Ответчик:**\n"
                        f"   {officer.mention}\n\n"
                        "━━━━━━━━━━ ЗАЯВЛЕНИЕ ━━━━━━━━━━\n\n"
                        f"Я, {inter.author.display_name}, проживающий в городе Макситаун,\n"
                        "обращаюсь в суд с настоящим заявлением по следующему делу:\n\n"
                        "━━━━━━━━━━ Содержание заявления ━━━━━━━━━━\n\n"
                        f"1️⃣ **Суть дела:**\n"
                        f"   {case_details}\n\n"
                        f"2️⃣ **Требования:**\n"
                        f"   {demands}\n\n"
                        f"3️⃣ **Доказательства:**\n"
                        f"   {evidence}\n\n"
                        f"4️⃣ **Дополнительные сведения:**\n"
                        f"   {additional_info if additional_info else 'Отсутствуют.'}\n\n"
                        "━━━━━━━━━━ Дата составления ━━━━━━━━━━\n\n"
                        f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y')}\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    
                    # Create appeal embed for the court forum
                    appeal_embed = disnake.Embed(
                        title=f"📜 Апелляция на штраф #{protocol_id}",
                        description=(
                            "━━━━━━━━━━ Информация об апелляции ━━━━━━━━━━\n\n"
                            f"👤 **Заявитель:** {inter.author.mention}\n"
                            f"👮 **Ответчик:** {officer.mention if officer else officer_name}\n"
                            f"💰 **Сумма штрафа:** {fine_amount:,}₽\n"
                            f"📅 **Дата подачи:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.blue()
                    )
                    
                    # Create thread in court forum
                    court_forum = bot.get_channel(1343172657742352434)  # Court forum channel ID
                    
                    if court_forum and isinstance(court_forum, disnake.ForumChannel):
                        # Create thread in court forum
                        court_thread = await court_forum.create_thread(
                            name=f"Апелляция на штраф #{protocol_id} - {inter.author.display_name}",
                            embed=appeal_embed,
                            content=f"{appeal_template}"  # Mention relevant roles
                        )
                        
                        # Update violation status to "appealed"
                        cursor.execute('''
                            UPDATE traffic_violations
                            SET status = 'appealed'
                            WHERE id = ?
                        ''', (protocol_id,))
                        conn.commit()
                        
                        # Send confirmation to the original thread
                        original_thread_embed = disnake.Embed(
                            title="⚖️ Подана апелляция",
                            description=(
                                f"Нарушитель {inter.author.mention} подал апелляцию на данный штраф.\n"
                                f"Дело передано в суд для рассмотрения.\n"
                                f"Ссылка на дело в суде: {court_thread.thread.jump_url}"
                            ),
                            color=disnake.Color.gold()
                        )
                        await inter.channel.send(embed=original_thread_embed)
                        
                        # Send confirmation to user
                        success_embed = disnake.Embed(
                            title="✅ Апелляция подана",
                            description=(
                                "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                                f"🔢 **ID протокола:** {protocol_id}\n"
                                f"⚖️ **Статус:** Передано в суд\n\n"
                                f"Ваша апелляция успешно подана в суд и будет рассмотрена в ближайшее время.\n"
                                f"Ссылка на дело в суде: {court_thread.thread.jump_url}\n\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            ),
                            color=disnake.Color.green()
                        )
                        await inter.edit_original_response(embed=success_embed)
                    else:
                        # Log error if forum channel not found
                        print(f"Error: Court forum channel not found or is not a forum channel")
                        await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Не удалось найти канал суда. Обратитесь к администрации.",
                                color=disnake.Color.red()
                            )
                        )
                
                except Exception as e:
                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description=f"Произошла ошибка при подаче апелляции: {str(e)}",
                            color=disnake.Color.red()
                        )
                    )
        
        # Send the modal
        await inter.response.send_modal(AppealModal())
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при подготовке апелляции: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)






@bot.slash_command(
    name="назначить_заседание",
    description="Назначить заседание суда по апелляции",
    guild_ids=[1341469479510474813]
)
async def schedule_hearing(inter: disnake.ApplicationCommandInteraction):
    """Slash command to schedule a court hearing"""
    try:
        # Check if the command is used in a thread in the court forum
        if not isinstance(inter.channel, disnake.Thread):
            return await inter.response.send_message("❌ Эта команда может использоваться только в треде с апелляцией.", ephemeral=True)
        
        # Check if user has judge role
        judge_role = disnake.utils.get(inter.guild.roles, name="Судья")
        if not judge_role or judge_role not in inter.author.roles:
            return await inter.response.send_message("❌ Только судьи могут назначать заседания суда.", ephemeral=True)
        
        # Create modal for scheduling
        class HearingScheduleModal(disnake.ui.Modal):
            def __init__(self):
                components = [
                    disnake.ui.TextInput(
                        label="Дополнительные приглашенные",
                        placeholder="Укажите имена и фамилии через запятую (Иван Иванов, Петр Петров)",
                        custom_id="additional_participants",
                        style=disnake.TextInputStyle.paragraph,
                        required=False,
                        max_length=1000
                    ),
                    disnake.ui.TextInput(
                        label="Дата заседания (ДД.ММ)",
                        placeholder="Например: 29.03",
                        custom_id="hearing_date",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=5
                    ),
                    disnake.ui.TextInput(
                        label="Время заседания (ЧЧ:ММ)",
                        placeholder="Например: 18:30",
                        custom_id="hearing_time",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=5
                    ),
                    disnake.ui.TextInput(
                        label="Комментарий к заседанию",
                        placeholder="Дополнительная информация о заседании",
                        custom_id="hearing_notes",
                        style=disnake.TextInputStyle.paragraph,
                        required=False,
                        max_length=500
                    )
                ]
                
                super().__init__(
                    title="Назначение судебного заседания",
                    components=components,
                    custom_id="hearing_schedule_modal"
                )
            
            async def callback(self, inter: disnake.ModalInteraction):
                await inter.response.defer(ephemeral=True)
                
                try:
                    additional_participants = inter.text_values["additional_participants"]
                    hearing_date = inter.text_values["hearing_date"]
                    hearing_time = inter.text_values["hearing_time"]
                    hearing_notes = inter.text_values["hearing_notes"]
                    
                    # Validate date format
                    try:
                        day, month = hearing_date.split('.')
                        day = int(day)
                        month = int(month)
                        if day < 1 or day > 31 or month < 1 or month > 12:
                            raise ValueError("Invalid date")
                    except:
                        return await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Неверный формат даты. Используйте формат ДД.ММ (например: 29.03)",
                                color=disnake.Color.red()
                            )
                        )
                    
                    # Validate time format
                    try:
                        hour, minute = hearing_time.split(':')
                        hour = int(hour)
                        minute = int(minute)
                        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                            raise ValueError("Invalid time")
                    except:
                        return await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Неверный формат времени. Используйте формат ЧЧ:ММ (например: 18:30)",
                                color=disnake.Color.red()
                            )
                        )
                    
                    # Get thread title to extract information
                    thread_title = inter.channel.name
                    
                    # Extract protocol ID and appellant name from thread title
                    # Format: "Апелляция на штраф #123 - Имя Фамилия"
                    protocol_id = None
                    appellant_name = None
                    
                    try:
                        if "Апелляция на штраф #" in thread_title:
                            parts = thread_title.split(" - ")
                            if len(parts) >= 2:
                                protocol_part = parts[0]
                                appellant_name = parts[1]
                                protocol_id = protocol_part.split("#")[1]
                    except:
                        pass
                    
                    # Get appellant and defendant from the database
                    appellant_id = None
                    defendant_id = None
                    
                    if protocol_id:
                        cursor.execute('''
                            SELECT violator_id, officer_id
                            FROM traffic_violations
                            WHERE id = ?
                        ''', (protocol_id,))
                        
                        violation_data = cursor.fetchone()
                        if violation_data:
                            appellant_id, defendant_id = violation_data
                    
                    # Get appellant and defendant users
                    appellant = None
                    defendant = None
                    
                    if appellant_id:
                        try:
                            appellant = await bot.fetch_user(appellant_id)
                        except:
                            pass
                    
                    if defendant_id:
                        try:
                            defendant = await bot.fetch_user(defendant_id)
                        except:
                            pass
                    
                    # Parse additional participants by name and find their Discord users
                    additional_users = []
                    additional_names = []
                    not_found_names = []
                    
                    if additional_participants:
                        # Split by commas
                        for participant_name in additional_participants.split(','):
                            participant_name = participant_name.strip()
                            if not participant_name:
                                continue
                                
                            additional_names.append(participant_name)
                            
                            # Find user by display name
                            found_user = None
                            for member in inter.guild.members:
                                # Check if the member's display name matches the participant name
                                if member.display_name.lower() == participant_name.lower():
                                    found_user = member
                                    break
                                    
                                # Also check if the name is in the format "Name Surname [tag]"
                                # Extract just the Name Surname part for comparison
                                if '[' in member.display_name:
                                    name_part = member.display_name.split('[')[0].strip()
                                    if name_part.lower() == participant_name.lower():
                                        found_user = member
                                        break
                            
                            if found_user:
                                additional_users.append(found_user)
                            else:
                                not_found_names.append(participant_name)
                    
                    # Create hearing embed
                    hearing_embed = disnake.Embed(
                        title="⚖️ Назначено судебное заседание",
                        description=(
                            "━━━━━━━━━━ Информация о заседании ━━━━━━━━━━\n\n"
                            f"📅 **Дата:** {hearing_date}.{datetime.now().year}\n"
                            f"⏰ **Время:** {hearing_time}\n"
                            f"👨‍⚖️ **Судья:** {inter.author.mention}\n\n"
                            "━━━━━━━━━━ Участники процесса ━━━━━━━━━━\n\n"
                        ),
                        color=disnake.Color.blue()
                    )
                    
                    # Add participants to description
                    participants_text = ""
                    if appellant:
                        participants_text += f"👤 **Истец:** {appellant.mention}\n"
                    
                    if defendant:
                        participants_text += f"👤 **Ответчик:** {defendant.mention}\n"
                    
                    if additional_users or not_found_names:
                        participants_text += f"👥 **Дополнительные участники:**\n"
                        
                        for user in additional_users:
                            participants_text += f"• {user.mention}\n"
                        
                        for name in not_found_names:
                            participants_text += f"• {name} (не найден на сервере)\n"
                    
                    hearing_embed.description += participants_text + "\n"
                    
                    # Add notes if provided
                    if hearing_notes:
                        hearing_embed.add_field(
                            name="📝 Комментарий",
                            value=hearing_notes,
                            inline=False
                        )
                    
                    # Add footer
                    hearing_embed.set_footer(text=f"Дело №{protocol_id if protocol_id else 'Неизвестно'} • Городской суд Макситауна")
                    
                    # Create mentions string for notification
                    mentions = []
                    if appellant:
                        mentions.append(appellant.mention)
                    if defendant:
                        mentions.append(defendant.mention)
                    for user in additional_users:
                        mentions.append(user.mention)
                    
                    mentions_text = " ".join(mentions) if mentions else ""
                    
                    # Send hearing announcement to the thread
                    await inter.channel.send(
                        embed=hearing_embed
                    )
                    
                    # Send confirmation to the judge
                    success_embed = disnake.Embed(
                        title="✅ Заседание назначено",
                        description=(
                            "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                            f"📅 **Дата и время:** {hearing_date}.{datetime.now().year} в {hearing_time}\n"
                            f"👥 **Количество участников:** {len(additional_names) + (1 if appellant else 0) + (1 if defendant else 0)}\n"
                            f"🔍 **Найдено пользователей:** {len(additional_users) + (1 if appellant else 0) + (1 if defendant else 0)}\n"
                            f"⚠️ **Не найдено пользователей:** {len(not_found_names)}\n\n"
                            "Уведомления о заседании отправлены всем найденным участникам в треде.\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.green()
                    )
                    await inter.edit_original_response(embed=success_embed)
                    
                    # Try to send DM notifications to participants
                    notification_embed = disnake.Embed(
                        title="⚖️ Вы приглашены на судебное заседание",
                        description=(
                            "━━━━━━━━━━ Информация о заседании ━━━━━━━━━━\n\n"
                            f"📅 **Дата:** {hearing_date}.{datetime.now().year}\n"
                            f"⏰ **Время:** {hearing_time}\n"
                            f"👨‍⚖️ **Судья:** {inter.author.display_name}\n"
                            f"🔗 **Ссылка на дело:** {inter.channel.jump_url}\n\n"
                            "Пожалуйста, будьте вовремя. Неявка может повлиять на решение суда.\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.blue()
                    )
                    
                    # Send DMs to all participants
                    all_participants = []
                    if appellant:
                        all_participants.append(appellant)
                    if defendant:
                        all_participants.append(defendant)
                    all_participants.extend(additional_users)
                    
                    for participant in all_participants:
                        try:
                            await participant.send(embed=notification_embed)
                        except:
                            # Ignore errors if DM can't be sent
                            pass
                
                except Exception as e:
                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description=f"Произошла ошибка при назначении заседания: {str(e)}",
                            color=disnake.Color.red()
                        )
                    )
        
        # Send the modal
        await inter.response.send_modal(HearingScheduleModal())
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при подготовке формы: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.response.send_message(embed=error_embed, ephemeral=True)

@bot.slash_command(
    name="вынести_вердикт",
    description="Вынести судебное решение по апелляции",
    guild_ids=[1341469479510474813]
)
async def issue_verdict(inter: disnake.ApplicationCommandInteraction):
    """Slash command to issue a court verdict"""
    try:
        # Check if the command is used in a thread in the court forum
        if not isinstance(inter.channel, disnake.Thread):
            return await inter.response.send_message("❌ Эта команда может использоваться только в треде с апелляцией.", ephemeral=True)
        
        # Check if user has judge role
        judge_role = disnake.utils.get(inter.guild.roles, name="Судья")
        if not judge_role or judge_role not in inter.author.roles:
            return await inter.response.send_message("❌ Только судьи могут выносить судебные решения.", ephemeral=True)
        
        # Get thread title to extract information
        thread_title = inter.channel.name
        
        # Extract protocol ID and appellant name from thread title
        # Format: "Апелляция на штраф #123 - Имя Фамилия"
        protocol_id = None
        appellant_name = None
        
        try:
            if "Апелляция на штраф #" in thread_title:
                parts = thread_title.split(" - ")
                if len(parts) >= 2:
                    protocol_part = parts[0]
                    appellant_name = parts[1]
                    protocol_id = protocol_part.split("#")[1]
        except:
            pass
        
        if not protocol_id:
            return await inter.response.send_message("❌ Не удалось определить номер протокола из названия треда.", ephemeral=True)
        
        # Get violation details from database
        cursor.execute('''
            SELECT violator_id, officer_id, fine_amount, status
            FROM traffic_violations
            WHERE id = ?
        ''', (protocol_id,))
        
        violation = cursor.fetchone()
        
        if not violation:
            return await inter.response.send_message("❌ Протокол о нарушении не найден в базе данных.", ephemeral=True)
        
        violator_id, officer_id, fine_amount, status = violation
        
        # Check if the violation is in appealed status
        if status != "appealed":
            return await inter.response.send_message("❌ Этот штраф не находится на рассмотрении в суде.", ephemeral=True)
        
        # Create modal for verdict
        class VerdictModal(disnake.ui.Modal):
            def __init__(self):
                components = [
                    disnake.ui.TextInput(
                        label="Решение суда",
                        placeholder="Виновен / Не виновен / Виновен частично",
                        custom_id="verdict_decision",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=50
                    ),
                    disnake.ui.TextInput(
                        label="Сумма штрафа (₽)",
                        placeholder="Введите сумму цифрами или 0, если штраф отменен",
                        custom_id="fine_amount",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=10
                    ),
                    disnake.ui.TextInput(
                        label="Дополнительные санкции",
                        placeholder="Укажите через запятую (например: лишение прав на 6 месяцев, общественные работы)",
                        custom_id="additional_sanctions",
                        style=disnake.TextInputStyle.paragraph,
                        required=False,
                        max_length=500
                    ),
                    disnake.ui.TextInput(
                        label="Обоснование решения",
                        placeholder="Укажите основания для принятого решения",
                        custom_id="verdict_reasoning",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        max_length=1000
                    )
                ]
                
                super().__init__(
                    title="Вынесение судебного решения",
                    components=components,
                    custom_id="verdict_modal"
                )
            
            async def callback(self, inter: disnake.ModalInteraction):
                await inter.response.defer(ephemeral=True)
                
                try:
                    verdict_decision = inter.text_values["verdict_decision"].strip()
                    fine_amount_text = inter.text_values["fine_amount"].strip()
                    additional_sanctions = inter.text_values["additional_sanctions"]
                    verdict_reasoning = inter.text_values["verdict_reasoning"]
                    
                    # Validate verdict decision
                    valid_decisions = ["виновен", "не виновен", "виновен частично"]
                    if verdict_decision.lower() not in valid_decisions:
                        return await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Решение суда должно быть одним из: Виновен / Не виновен / Виновен частично",
                                color=disnake.Color.red()
                            )
                        )
                    
                    # Validate fine amount
                    if not fine_amount_text.isdigit():
                        return await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Сумма штрафа должна быть указана цифрами.",
                                color=disnake.Color.red()
                            )
                        )
                    
                    new_fine_amount = int(fine_amount_text)
                    if new_fine_amount < 0:
                        return await inter.edit_original_response(
                            embed=disnake.Embed(
                                title="❌ Ошибка",
                                description="Сумма штрафа не может быть отрицательной.",
                                color=disnake.Color.red()
                            )
                        )
                    
                    # Get appellant and officer users
                    appellant = None
                    officer = None
                    
                    if violator_id:
                        try:
                            appellant = await bot.fetch_user(violator_id)
                        except:
                            pass
                    
                    if officer_id:
                        try:
                            officer = await bot.fetch_user(officer_id)
                        except:
                            pass
                    
                    # Format the verdict template
                    verdict_template = (
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "📜 **РЕШЕНИЕ СУДА**\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        "**ИМЕНЕМ РОССИЙСКОЙ ФЕДЕРАЦИИ**\n\n"
                        f"Городской суд города Макситаун в составе:\n"
                        f"председательствующего судьи {inter.author.mention},\n"
                        f"при секретаре заседания суда Максичай,\n"
                        f"рассмотрев в открытом судебном заседании дело по апелляционной жалобе\n"
                        f"{appellant.mention if appellant else appellant_name} на постановление о наложении штрафа №{protocol_id},\n\n"
                        "**УСТАНОВИЛ:**\n\n"
                        f"{verdict_reasoning}\n\n"
                        "**ПОСТАНОВИЛ:**\n\n"
                        f"Признать гражданина {appellant.mention if appellant else appellant_name} **{verdict_decision}** в совершении правонарушения.\n\n"
                    )
                    
                    # Add fine information based on verdict
                    if verdict_decision.lower() == "не виновен":
                        verdict_template += (
                            f"Отменить штраф в размере {fine_amount:,}₽, наложенный постановлением №{protocol_id}.\n\n"
                        )
                    elif new_fine_amount == 0:
                        verdict_template += (
                            f"Отменить штраф в размере {fine_amount:,}₽, наложенный постановлением №{protocol_id}.\n\n"
                        )
                    elif new_fine_amount != fine_amount:
                        verdict_template += (
                            f"Изменить сумму штрафа с {fine_amount:,}₽ на {new_fine_amount:,}₽.\n\n"
                        )
                    else:
                        verdict_template += (
                            f"Оставить в силе штраф в размере {fine_amount:,}₽, наложенный постановлением №{protocol_id}.\n\n"
                        )
                    
                    # Add additional sanctions if provided
                    if additional_sanctions:
                        verdict_template += (
                            f"**Дополнительные санкции:**\n"
                            f"{additional_sanctions}\n\n"
                        )
                    
                    # Add footer
                    verdict_template += (
                        f"Решение вступает в силу немедленно.\n\n"
                        f"Судья: {inter.author.display_name}\n"
                        f"Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    
                    # Create verdict embed
                    verdict_embed = disnake.Embed(
                        title=f"⚖️ Решение суда по делу №{protocol_id}",
                        description=verdict_template,
                        color=disnake.Color.dark_blue()
                    )
                    
                    # Send verdict to the thread
                    mentions = []
                    if appellant:
                        mentions.append(appellant.mention)
                    if officer:
                        mentions.append(officer.mention)
                    
                    mentions_text = " ".join(mentions) if mentions else ""
                    
                    await inter.channel.send(
                        content=mentions_text,
                        embed=verdict_embed
                    )
                    
                    # Update violation status and fine amount in database
                    new_status = "active"  # Default status if fine is still active
                    
                    if verdict_decision.lower() == "не виновен" or new_fine_amount == 0:
                        new_status = "cancelled"  # Cancel the fine
                    else:
                        new_status = "modified" if new_fine_amount != fine_amount else "active"
                    
                    cursor.execute('''
                        UPDATE traffic_violations
                        SET status = ?, fine_amount = ?
                        WHERE id = ?
                    ''', (new_status, new_fine_amount, protocol_id))
                    conn.commit()
                    
                    # Send confirmation to the judge
                    success_embed = disnake.Embed(
                        title="✅ Решение вынесено",
                        description=(
                            "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                            f"🔢 **ID протокола:** {protocol_id}\n"
                            f"⚖️ **Решение:** {verdict_decision}\n"
                            f"💰 **Штраф:** {new_fine_amount:,}₽ "
                            f"({'отменен' if new_status == 'cancelled' else 'изменен' if new_status == 'modified' else 'оставлен без изменений'})\n\n"
                            "Решение суда опубликовано в треде и вступило в силу.\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=disnake.Color.green()
                    )
                    await inter.edit_original_response(embed=success_embed)
                    
                    # Send notification to the original violation thread
                    try:
                        # Get the original thread
                        cursor.execute('''
                            SELECT thread_id
                            FROM traffic_violations
                            WHERE id = ?
                        ''', (protocol_id,))
                        
                        original_thread_data = cursor.fetchone()
                        if original_thread_data:
                            original_thread_id = original_thread_data[0]
                            original_thread = bot.get_channel(original_thread_id)
                            
                            if original_thread:
                                # Create notification embed
                                notification_embed = disnake.Embed(
                                    title="⚖️ Решение суда",
                                    description=(
                                        f"По апелляции на штраф #{protocol_id} вынесено судебное решение.\n\n"
                                        f"**Решение:** {verdict_decision}\n"
                                        f"**Штраф:** {new_fine_amount:,}₽ "
                                        f"({'отменен' if new_status == 'cancelled' else 'изменен' if new_status == 'modified' else 'оставлен без изменений'})\n\n"
                                        f"**Судья:** {inter.author.mention}\n"
                                        f"**Дата:** {datetime.now().strftime('%d.%m.%Y')}\n\n"
                                        f"Полный текст решения: {inter.channel.jump_url}"
                                    ),
                                    color=disnake.Color.dark_blue()
                                )
                                
                                await original_thread.send(embed=notification_embed)
                    except Exception as e:
                        print(f"Error sending notification to original thread: {e}")
                    
                    # Send DM notification to appellant
                    if appellant:
                        try:
                            dm_embed = disnake.Embed(
                                title="⚖️ Решение суда по вашей апелляции",
                                description=(
                                    f"По вашей апелляции на штраф #{protocol_id} вынесено судебное решение.\n\n"
                                    f"**Решение:** {verdict_decision}\n"
                                    f"**Штраф:** {new_fine_amount:,}₽ "
                                    f"({'отменен' if new_status == 'cancelled' else 'изменен' if new_status == 'modified' else 'оставлен без изменений'})\n\n"
                                    f"**Судья:** {inter.author.mention}\n"
                                    f"**Дата:** {datetime.now().strftime('%d.%m.%Y')}\n\n"
                                    f"Полный текст решения: {inter.channel.jump_url}"
                                ),
                                color=disnake.Color.dark_blue()
                            )
                            
                            await appellant.send(embed=dm_embed)
                        except:
                            pass
                
                except Exception as e:
                    await inter.edit_original_response(
                        embed=disnake.Embed(
                            title="❌ Ошибка",
                            description=f"Произошла ошибка при вынесении решения: {str(e)}",
                            color=disnake.Color.red()
                        )
                    )
        
        # Send the modal
        await inter.response.send_modal(VerdictModal())
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при подготовке формы: {str(e)}",
            color=disnake.Color.red()
        )
        await inter.response.send_message(embed=error_embed, ephemeral=True)

@bot.command()
async def обновить_разрешения(ctx):
    """Updates vehicle spawn permissions for all users based on their owned cars, rentals, and jobs"""
    # Check if user has admin permissions
    if not ctx.author.guild_permissions.administrator:
        embed = disnake.Embed(
            title="❌ Недостаточно прав",
            description="Эта команда доступна только администраторам",
            color=disnake.Color.red()
        )
        return await ctx.send(embed=embed)
    
    try:
        # Initial response
        initial_embed = disnake.Embed(
            title="⌛ Обновление разрешений...",
            description="Пожалуйста, подождите, идет обработка разрешений на спавн транспорта для всех пользователей...",
            color=disnake.Color.yellow()
        )
        message = await ctx.send(embed=initial_embed)
        
        # Get all users with purchased cars
        cursor.execute('SELECT DISTINCT buyer_id FROM purchased_cars')
        user_ids = [row[0] for row in cursor.fetchall()]
        
        # Get all users with active rentals
        cursor.execute('''
            SELECT DISTINCT renter_id FROM rentcar 
            WHERE status = 'active' AND end_time > ?
        ''', (datetime.now().isoformat(),))
        renter_ids = [row[0] for row in cursor.fetchall()]
        
        # Get all users with jobs
        cursor.execute('SELECT DISTINCT user_id FROM user_jobs')
        job_user_ids = [row[0] for row in cursor.fetchall()]
        
        # Combine all user IDs (remove duplicates)
        all_user_ids = list(set(user_ids + renter_ids + job_user_ids))
        
        # Process statistics
        total_users = len(all_user_ids)
        processed_users = 0
        successful_users = 0
        failed_users = 0
        total_vehicles_added = 0
        
        # Process each user
        for user_id in all_user_ids:
            try:
                # Get user object
                member = None
                try:
                    member = await ctx.guild.fetch_member(user_id)
                except:
                    # User might not be in the guild anymore
                    continue
                
                if not member:
                    continue
                
                display_name = member.display_name
                
                # Get all cars owned by the user
                cursor.execute('''
                    SELECT brand, model 
                    FROM purchased_cars 
                    WHERE buyer_id = ?
                ''', (user_id,))
                owned_cars = cursor.fetchall()
                
                # Get all rented cars
                cursor.execute('''
                    SELECT pc.brand, pc.model
                    FROM rentcar rc
                    JOIN purchased_cars pc ON rc.car_id = pc.id
                    WHERE rc.renter_id = ? AND rc.status = 'active'
                    AND rc.end_time > ?
                ''', (user_id, datetime.now().isoformat()))
                rented_cars = cursor.fetchall()
                
                # Combine owned and rented cars
                all_cars = owned_cars + rented_cars
                
                # Get job-related vehicles
                job_vehicles = []
                
                # Get user's jobs from user_jobs table
                cursor.execute('SELECT job_id FROM user_jobs WHERE user_id = ?', (user_id,))
                job_ids = [row[0] for row in cursor.fetchall()]
                
                # Get vehicles for each job from addjobs table
                for job_id in job_ids:
                    cursor.execute('SELECT car FROM addjobs WHERE job_id = ?', (job_id,))
                    job_cars = [row[0] for row in cursor.fetchall()]
                    job_vehicles.extend(job_cars)
                
                # Process all vehicles for this user
                user_success = True
                vehicles_added = 0
                
                # Process owned and rented cars
                for brand, model in all_cars:
                    vehicle_name = f"{brand} {model}"
                    result = await carmanager(display_name, "добавить", vehicle_name)
                    if result:
                        vehicles_added += 1
                    else:
                        user_success = False
                
                # Process job vehicles
                for vehicle in job_vehicles:
                    result = await carmanager(display_name, "добавить", vehicle)
                    if result:
                        vehicles_added += 1
                    else:
                        user_success = False
                
                # Update statistics
                processed_users += 1
                if user_success:
                    successful_users += 1
                else:
                    failed_users += 1
                total_vehicles_added += vehicles_added
                
                # Update progress every 5 users
                if processed_users % 5 == 0:
                    progress_embed = disnake.Embed(
                        title="⌛ Обновление разрешений...",
                        description=f"Обработано {processed_users}/{total_users} пользователей...",
                        color=disnake.Color.yellow()
                    )
                    await message.edit(embed=progress_embed)
                
            except Exception as e:
                print(f"Error processing user {user_id}: {e}")
                failed_users += 1
                processed_users += 1
        
        # Create result embed
        result_embed = disnake.Embed(
            title="✅ Обновление разрешений завершено",
            color=disnake.Color.green()
        )
        
        # Add summary field
        result_embed.add_field(
            name="📊 Сводка",
            value=(
                "━━━━━━━━━━ Результаты обработки ━━━━━━━━━━\n\n"
                f"👥 **Всего пользователей:** {total_users}\n"
                f"✅ **Успешно обработано:** {successful_users} пользователей\n"
                f"❌ **Ошибки при обработке:** {failed_users} пользователей\n"
                f"🚗 **Всего добавлено ТС:** {total_vehicles_added}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            inline=False
        )
        
        result_embed.set_footer(text=f"Обработка завершена • {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        await message.edit(embed=result_embed)
        
        # Log the action
        logs_channel = bot.get_channel(1351455653197123665)
        logs_embed = disnake.Embed(
            title="🔄 Массовое обновление разрешений",
            description=(
                "━━━━━━━━━━ Информация об операции ━━━━━━━━━━\n\n"
                f"👤 **Администратор:** {ctx.author.mention}\n"
                f"👥 **Обработано пользователей:** {processed_users}/{total_users}\n"
                f"🚗 **Добавлено ТС:** {total_vehicles_added}\n"
                f"📅 **Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.blue()
        )
        await logs_channel.send(embed=logs_embed)
        
    except Exception as e:
        error_embed = disnake.Embed(
            title="❌ Ошибка",
            description=f"Произошла ошибка при обновлении разрешений: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)




def load_car_names_mapping():
    try:
        # Use relative path to the current script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cars_json_path = os.path.join(script_dir, "cars_names.json")
        
        with open(cars_json_path, "r", encoding="utf-8") as f:
            car_mapping = json.load(f)
            # Create reverse mapping (display name -> internal name)
            reverse_mapping = {v.lower(): k for k, v in car_mapping.items()}
            return car_mapping, reverse_mapping
    except Exception as e:
        print(f"Error loading car names mapping: {e}")
        return {}, {}

# Load car mappings at startup
car_mapping, reverse_car_mapping = load_car_names_mapping()

# Function to convert car name to internal format
def convert_car_name(car_name):
    """Convert user-friendly car name to internal BeamMP format"""
    car_name_lower = car_name.lower()
    
    # Check if the car name exists in our reverse mapping
    if car_name_lower in reverse_car_mapping:
        internal_car_name = reverse_car_mapping[car_name_lower]
        display_name = car_name
    else:
        # Check if it's already an internal name
        if car_name in car_mapping:
            internal_car_name = car_name
            display_name = car_mapping[car_name]
        else:
            internal_car_name = car_name
            display_name = car_name
    
    return internal_car_name, display_name

async def carmanager(discord_name: str, action: str, car_name: str = None):
    try:
        # Extract BeamMP nickname from discord_name
        if '[' in discord_name and ']' in discord_name:
            beammp_nick = discord_name.split('[')[1].split(']')[0]
        else:
            print("Неверный формат имени игрока. Используйте формат: Имя[Ник_BeamMP]")
            return
        
        # Check if action is valid
        action = action.lower()
        if action not in ["добавить", "удалить"]:
            print("Неверное действие.")
        
        # For both actions, car_name is required
        if not car_name:
            print("Необходимо указать название машины.")
        # Convert car name to internal format using the local function
        internal_car_name, display_name = convert_car_name(car_name)
        
        # If the car wasn't found in the mapping, send a warning
        if internal_car_name == car_name and display_name == car_name and car_name not in car_mapping:
            print("авто не найдено.")
        
        # Perform the requested action
        if action == "добавить":
            result = add_car_to_player(beammp_nick, internal_car_name)
            if result:
                return True
            else:
                return False
        else:  # action == "удалить"
            result = remove_car_from_player(beammp_nick, internal_car_name)
            if result:
                return True
            else:
                return False
    
    except Exception as e:
        await ctx.send(
            embed=disnake.Embed(
                title="❌ Ошибка",
                description=f"Произошла ошибка при выполнении команды: {str(e)}",
                color=disnake.Color.red()
            )
        )
        return False

@bot.command()
@commands.has_permissions(administrator=True)
async def removemon(ctx, user: disnake.Member, price: int):
    """Command to remove money from a user's balance"""
    try:
        # Get current user balance
        bal = unbclient.get_user_bal(1341469479510474813, user.id)
        
        # Calculate new balance after deduction
        new_buyer_bal = bal['cash'] - price
        
        # Update user balance
        unbclient.set_user_bal(1341469479510474813, user.id, cash=new_buyer_bal)
        
        # Create success embed
        success_embed = disnake.Embed(
            title="💰 Баланс обновлён",
            description=(
                "━━━━━━━━━━ Детали Операции ━━━━━━━━━━\n\n"
                f"👤 **Пользователь:** {user.mention}\n"
                f"💵 **Сумма:** {price:,}₽\n"
                f"💰 **Новый баланс:** {new_buyer_bal:,}₽\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        await ctx.send(embed=success_embed)
        
    except Exception as e:
        # Create error embed
        error_embed = disnake.Embed(
            title="❌ Error",
            description=f"Failed to update balance: {str(e)}",
            color=disnake.Color.red()
        )
        await ctx.send(embed=error_embed)



@bot.slash_command(
    name="автошкола",
    description="Команды для управления автошколой",
    guild_ids=[1341469479510474813]
)
async def driving_school(inter: disnake.ApplicationCommandInteraction):
    """Group command for driving school management"""
    pass

@driving_school.sub_command(
    name="начать_экзамен",
    description="Начать экзамен по вождению для ученика"
)
@commands.has_any_role("Инструктор категории B","Инструктор категории C","Инструктор категории D", "Администратор")
async def start_exam(
    inter: disnake.ApplicationCommandInteraction,
    ученик: disnake.Member = commands.Param(description="Ученик, сдающий экзамен"),
    категория: str = commands.Param(
        description="Категория прав", 
        choices=["B", "C", "D", "E"]
    )
):
    """Start a driving exam for a student"""
    try:
        await inter.response.defer(ephemeral=True)
        
        student_display_name = ученик.display_name
        
        if '[' not in student_display_name or ']' not in student_display_name:
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Ошибка",
                    description=f"У ученика {ученик.mention} неправильный формат никнейма. Требуется формат: Имя [Ник_BeamMP]",
                    color=disnake.Color.red()
                )
            )
        
        cursor.execute('''
            SELECT category, status FROM licenses 
            WHERE user_id = ? AND category = ?
        ''', (str(ученик.id), категория))
        
        existing_license = cursor.fetchone()
        if existing_license and existing_license[1] == "active":
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Ошибка",
                    description=f"У ученика {ученик.mention} уже есть действующие права категории {категория}",
                    color=disnake.Color.red()
                )
            )
        
        test_vehicle = "Lada2110"  
        
        cursor.execute('''
            INSERT INTO driving_exams 
            (student_id, instructor_id, category, status, start_time)
            VALUES (?, ?, ?, 'in_progress', ?)
        ''', (
            ученик.id, inter.author.id, категория, datetime.now().isoformat()
        ))
        conn.commit()
        
        exam_id = cursor.lastrowid
        
        try:
            beammp_name = student_display_name.split('[')[1].split(']')[0]
            result = add_car_to_player(beammp_name, test_vehicle)
            
            if not result:
                cursor.execute('''
                    UPDATE driving_exams
                    SET status = 'failed', end_time = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), exam_id))
                conn.commit()
                
                return await inter.edit_original_response(
                    embed=disnake.Embed(
                        title="❌ Ошибка",
                        description=f"Не удалось выдать тестовый автомобиль ученику {ученик.mention}. Проверьте правильность никнейма.",
                        color=disnake.Color.red()
                    )
                )
        except Exception as e:
            cursor.execute('''
                UPDATE driving_exams
                SET status = 'failed', end_time = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), exam_id))
            conn.commit()
            
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Ошибка",
                    description=f"Произошла ошибка при выдаче автомобиля: {str(e)}",
                    color=disnake.Color.red()
                )
            )
        
        success_embed = disnake.Embed(
            title="🚗 Экзамен начат",
            description=(
                "━━━━━━━━━━ Информация об экзамене ━━━━━━━━━━\n\n"
                f"👤 **Ученик:** {ученик.mention}\n"
                f"🔰 **Категория прав:** {категория}\n"
                f"🚘 **Тестовый автомобиль:** {test_vehicle}\n"
                f"👨‍🏫 **Инструктор:** {inter.author.mention}\n"
                f"🔢 **ID экзамена:** {exam_id}\n\n"
                f"Для завершения экзамена используйте команду:\n"
                f"`/автошкола завершить_экзамен {exam_id} [результат]`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green()
        )
        
        await inter.edit_original_response(embed=success_embed)
        
        try:
            student_embed = disnake.Embed(
                title="🚗 Экзамен по вождению начат",
                description=(
                    "━━━━━━━━━━ Информация ━━━━━━━━━━\n\n"
                    f"🔰 **Категория прав:** {категория}\n"
                    f"🚘 **Тестовый автомобиль:** {test_vehicle}\n"
                    f"👨‍🏫 **Инструктор:** {inter.author.display_name}\n\n"
                    f"Вам выдан доступ к тестовому автомобилю. Следуйте указаниям инструктора.\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.blue()
            )
            await ученик.send(embed=student_embed)
        except:
            pass
        

        log_channel = bot.get_channel(1351455653197123665)  
        if log_channel:
            log_embed = disnake.Embed(
                title="🚗 Начат экзамен в автошколе",
                description=(
                    f"👤 **Ученик:** {ученик.mention}\n"
                    f"🔰 **Категория прав:** {категория}\n"
                    f"👨‍🏫 **Инструктор:** {inter.author.mention}\n"
                    f"⏰ **Время начала:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                ),
                color=disnake.Color.blue()
            )
            await log_channel.send(embed=log_embed)
        
    except Exception as e:
        await inter.edit_original_response(
            embed=disnake.Embed(
                title="❌ Ошибка",
                description=f"Произошла ошибка при начале экзамена: {str(e)}",
                color=disnake.Color.red()
            )
        )

@driving_school.sub_command(
    name="завершить_экзамен",
    description="Завершить экзамен по вождению и выставить результат"
)
@commands.has_any_role("Инструктор категории B","Инструктор категории C","Инструктор категории D", "Администратор")
async def finish_exam(
    inter: disnake.ApplicationCommandInteraction,
    экзамен_id: int = commands.Param(description="ID экзамена"),
    результат: str = commands.Param(
        description="Результат экзамена", 
        choices=["сдал", "не сдал"]
    )
):
    """Finish a driving exam and set the result"""
    try:
        await inter.response.defer(ephemeral=True)
        

        cursor.execute('''
            SELECT student_id, instructor_id, category, status
            FROM driving_exams
            WHERE id = ?
        ''', (экзамен_id,))
        
        exam_data = cursor.fetchone()
        
        if not exam_data:
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Ошибка",
                    description=f"Экзамен с ID {экзамен_id} не найден",
                    color=disnake.Color.red()
                )
            )
        
        student_id, instructor_id, category, status = exam_data
        

        if status != "in_progress":
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Ошибка",
                    description=f"Экзамен с ID {экзамен_id} уже завершен",
                    color=disnake.Color.red()
                )
            )
        

        if instructor_id != inter.author.id and not any(role.name == "Администратор" for role in inter.author.roles):
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Ошибка",
                    description="Вы не можете завершить экзамен, который начал другой инструктор",
                    color=disnake.Color.red()
                )
            )
        
        # Get student
        try:
            student = await bot.fetch_user(student_id)
            student_member = await inter.guild.fetch_member(student_id)
            student_display_name = student_member.display_name
        except:
            return await inter.edit_original_response(
                embed=disnake.Embed(
                    title="❌ Ошибка",
                    description="Не удалось найти ученика, связанного с этим экзаменом",
                    color=disnake.Color.red()
                )
            )
        

        test_vehicle = "Lada2110"  #
        try:

            beammp_name = student_display_name.split('[')[1].split(']')[0]
            remove_car_from_player(beammp_name, test_vehicle)
        except Exception as e:

            print(f"Error removing test vehicle: {e}")
        

        new_status = "passed" if результат == "сдал" else "failed"
        cursor.execute('''
            UPDATE driving_exams
            SET status = ?, result = ?, end_time = ?
            WHERE id = ?
        ''', (new_status, результат, datetime.now().isoformat(), экзамен_id))
        

        if результат == "сдал":

            cursor.execute('''
                SELECT category, status FROM licenses
                WHERE user_id = ? AND category = ?
            ''', (str(student_id), category))
            
            existing_license = cursor.fetchone()
            
            if existing_license:
                cursor.execute('''
                    UPDATE licenses
                    SET issue_date = ?, status = "active"
                    WHERE user_id = ? AND category = ?
                ''', (datetime.now().isoformat(), str(student_id), category))
            else:
                cursor.execute('''
                    INSERT INTO licenses
                    (user_id, category, issue_date, status)
                    VALUES (?, ?, ?, "active")
                ''', (str(student_id), category, datetime.now().isoformat()))
        
        conn.commit()
        

        result_embed = disnake.Embed(
            title=f"{'✅ Экзамен сдан' if результат == 'сдал' else '❌ Экзамен не сдан'}",
            description=(
                "━━━━━━━━━━ Результаты экзамена ━━━━━━━━━━\n\n"
                f"👤 **Ученик:** {student.mention}\n"
                f"🔰 **Категория прав:** {category}\n"
                f"📝 **Результат:** {результат.upper()}\n"
                f"👨‍🏫 **Инструктор:** {inter.author.mention}\n"
                f"⏰ **Время завершения:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"{'🎉 Водительское удостоверение категории ' + category + ' выдано!' if результат == 'сдал' else '😔 Попробуйте сдать экзамен еще раз.'}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=disnake.Color.green() if результат == 'сдал' else disnake.Color.red()
        )
        

        await inter.channel.send(
            content=student.mention,
            embed=result_embed
        )

        await inter.edit_original_response(
            embed=disnake.Embed(
                title="✅ Экзамен завершен",
                description=f"Экзамен для {student.mention} успешно завершен с результатом: {результат}",
                color=disnake.Color.green()
            )
        )
        
        try:
            student_embed = disnake.Embed(
                title=f"{'✅ Вы сдали экзамен!' if результат == 'сдал' else '❌ Экзамен не сдан'}",
                description=(
                    "━━━━━━━━━━ Результаты экзамена ━━━━━━━━━━\n\n"
                    f"🔰 **Категория прав:** {category}\n"
                    f"📝 **Результат:** {результат.upper()}\n"
                    f"👨‍🏫 **Инструктор:** {inter.author.display_name}\n\n"
                    f"{'🎉 Поздравляем! Вам выдано водительское удостоверение категории ' + category + '.' if результат == 'сдал' else '😔 К сожалению, вы не сдали экзамен. Вы можете попробовать еще раз после дополнительной подготовки.'}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=disnake.Color.green() if результат == 'сдал' else disnake.Color.red()
            )
            await student.send(embed=student_embed)
        except:
            pass
        
        log_channel = bot.get_channel(1351455653197123665) 
        if log_channel:
            log_embed = disnake.Embed(
                title=f"🚗 Завершен экзамен в автошколе",
                description=(
                    f"👤 **Ученик:** {student.mention}\n"
                    f"🔰 **Категория прав:** {category}\n"
                    f"📝 **Результат:** {результат.upper()}\n"
                    f"👨‍🏫 **Инструктор:** {inter.author.mention}\n"
                    f"⏰ **Время завершения:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                ),
                color=disnake.Color.green() if результат == 'сдал' else disnake.Color.red()
            )
            await log_channel.send(embed=log_embed)
        
    except Exception as e:
        await inter.edit_original_response(
            embed=disnake.Embed(
                title="❌ Ошибка",
                description=f"Произошла ошибка при завершении экзамена: {str(e)}",
                color=disnake.Color.red()
            )
        )







bot.run(discord_token)