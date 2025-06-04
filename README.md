# AnkiBot Discord Bot

AnkiBot is a Discord bot designed to provide various functionalities, including fetching random quotes, responding to ping commands, and providing help information about available commands. This bot is built using the Discord.py library and is structured to keep command definitions organized in separate files.

## Project Structure

```
AnkiBot
├── bot.py                  # Main entry point for the Discord bot
├── commands                # Directory containing command groups
│   ├── help_commands.py    # Defines the help command group
│   ├── ...                 # And all other command groups are like this
├── .env                    # Environment variables for the bot - Copy the .example.env and fill in your own variables!
├── .example.env            # Template for the .env file
├── .gitignore              # Specifies files to ignore in Git
└── README.md               # Documentation for the project
```

## Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd AnkiBot
   ```

2. **Install Dependencies**
   Make sure you have Python 3.8 or higher installed. Then, install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Copy the `.example.env` file to `.env` and fill in the required values:

   ```bash
   cp .example.env .env
   ```

   Fill in its values.

4. **Run the Bot**
   Execute the bot using the following command:
   ```bash
   python bot.py
   ```

## Usage

- **Help Command**: Use `/help` to get a list of available commands.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

If you add **ANYTHING** at all, please drop your name in the `data/contributers.py`! All help counts.

## License

This project is licensed under the MIT License. Feel free to propose any changes.
