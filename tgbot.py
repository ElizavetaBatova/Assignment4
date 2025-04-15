import math
from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackContext
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

application = Application.builder().token("8061586136:AAFyi65FyY-ZsLNX-I1W0tGmmxf9UX46C_Y").build() #We took token from BotFather

async def start(update, context):
    await update.message.reply_text("Welcome to Financial Planner Bot! To see all the available commands use /help")

application.add_handler(CommandHandler("start", start))

async def help(update, context):
    await update.message.reply_text("""This bot was created to help you collect data about your budget. Use commands:
 /config - to configure income & budgets per category
 /log - to log expenses & income with categories
 /summary - to view balance & budget summaries
 /notifyon - to set push notifications
 /notifyoff - to delete push notifications""")
application.add_handler(CommandHandler("help", help))

CATEGORY, INCOME, BUDGET = range(3) #We have 3 main variable

user_data = {} 

async def config(update: Update, context: CallbackContext):
    await update.message.reply_text("Print your category:")
    return CATEGORY 

async def category(update: Update, context: CallbackContext):
    context.user_data["category"] = update.message.text #It is text and will not be converted into numerals in any case
    await update.message.reply_text("Print income for the category:")
    return INCOME

async def income(update: Update, context: CallbackContext):
    context.user_data["income"] = float(update.message.text) #We had to convert it into float to make it possible use math (log function) in the future
    await update.message.reply_text("Print budget for the category:")
    return BUDGET

async def budget(update: Update, context: CallbackContext):
    context.user_data["budget"] = float(update.message.text) #This one is the same as income :>
    await update.message.reply_text(f"Saved! Category: {context.user_data['category']}, Income: {context.user_data['income']}, Budget: {context.user_data['budget']}")
    return ConversationHandler.END 

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Configuration canceled.")
    return ConversationHandler.END

config_handler = ConversationHandler(
    entry_points=[CommandHandler("config", config)],
    states={
        CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, category)],
        INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, income)],
        BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(config_handler)


logging.basicConfig(level=logging.INFO)

async def log(update: Update, context: CallbackContext):
    user_data = context.user_data

    logging.info(f"User data: {user_data}")  #Print stored values

    if "category" in user_data and "income" in user_data and "budget" in user_data:
        try:
            income_log = math.log(user_data["income"])  #No need to convert it here, because we've done it earlier
            budget_log = math.log(user_data["budget"]) #Here too
            
            response = (
                f"📊 Expense & Income Log:\n"
                f"🔹 Category: {user_data['category']}\n"
                f"💰 Log(Income): {income_log:.2f}\n"
                f"📉 Log(Budget): {budget_log:.2f}\n"
            )
        except ValueError:
            response = "Error: Income or Budget must be a number!"
    else:
        response = "No data found! Use /config to set up categories and budgets."

    await update.message.reply_text(response)   

application.add_handler(CommandHandler("log", log))

async def summary(update: Update, context: CallbackContext):
    user_data = context.user_data

    if not user_data:
        await update.message.reply_text("No financial data found! Use /config to set up categories and budgets.")
        return

    response = "📊 Your Financial Planner Summary:\n"
    
    try:
        category = user_data.get("category", "N/A")
        income = float(user_data.get("income", 0))  
        budget = float(user_data.get("budget", 0))
        
        income_log = math.log(income) if income > 0 else 0
        budget_log = math.log(budget) if budget > 0 else 0

        response += (
            f"🔹 Category: {category}\n"
            f"💰 Income: {income:.2f} | Log(Income): {income_log:.2f}\n"
            f"📉 Budget: {budget:.2f} | Log(Budget): {budget_log:.2f}\n"
        )

    except ValueError:
        response = "Error: Income or Budget must be valid numbers!"

    await update.message.reply_text(response)

application.add_handler(CommandHandler("summary", summary))

scheduler = BackgroundScheduler()

async def send_summary(context: CallbackContext):
    """Function that sends a daily financial summary."""
    job = context.job
    user_data = context.bot_data.get(job.name, {}) 

    if not user_data:
        await context.bot.send_message(job.context, text="No financial data found! Use /config to set up categories and budgets.")
        return

    try:
        category = user_data.get("category", "N/A")
        income = float(user_data.get("income", 0))  
        budget = float(user_data.get("budget", 0))
        
        income_log = math.log(income) if income > 0 else 0
        budget_log = math.log(budget) if budget > 0 else 0

        message = (
            f"📊 Daily Financial Summary:\n"
            f"🔹 Category: {category}\n"
            f"💰 Income: {income:.2f} | Log(Income): {income_log:.2f}\n"
            f"📉 Budget: {budget:.2f} | Log(Budget): {budget_log:.2f}\n"
        )
        await context.bot.send_message(job.context, text=message)

    except ValueError:
        await context.bot.send_message(job.context, text="Error: Income or Budget must be valid numbers!")

async def notifyon(update: Update, context: CallbackContext):
    """Command to enable notifications."""
    chat_id = update.message.chat_id

    scheduler.add_job(send_summary, "interval", hours=24, name=str(chat_id), context=chat_id)

    await update.message.reply_text("✅ Daily push notifications enabled! You'll receive financial updates every day.")

async def notifyoff(update: Update, context: CallbackContext):
    """Command to disable notifications."""
    chat_id = update.message.chat_id

    job = scheduler.get_job(str(chat_id))
    if job:
        job.remove()

    await update.message.reply_text("❌ Push notifications disabled.")

scheduler.start()

application.add_handler(CommandHandler("notifyon", notifyon))
application.add_handler(CommandHandler("notifyoff", notifyoff))


application.run_polling()
