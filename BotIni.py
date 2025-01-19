from BotFunctionality import *


if __name__ == "__main__":
    application = ApplicationBuilder().token("7547777250:AAHQHE_IG1QY70aIwBXTuQ2WIEvt3JrFlxE").build()
 

     
    # application.add_handler(MessageHandler(filters.TEXT, bot_talking)) # сделать из бота тупо говорилку!

    application.add_handler(CommandHandler("start",start)) # для отображения меню с кнопками обязательно!
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    # application.add_handler(CommandHandler("search", search_command))

    # application.add_handler(CommandHandler("help", help_command))
    # application.add_handler(CommandHandler("newPicture", create_command))
    # application.add_handler(CommandHandler("setSettings", setting_command))
    
    application.run_polling()

   


