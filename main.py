import discord
import os
import dropbox
import random
from dotenv import load_dotenv
from dropbox.exceptions import ApiError
import asyncio

# To-DO main things
# Need a way to automate this... to use a command weekly at a specific time
# See how to host this. Time to ask friends

load_dotenv() # Makes sure to get all env tokens loaded

IMAGE_FOLDER = "images"
DROPBOX_IMAGES = "/my_images_discord"  # This is what I named it... but probably removing it laters
# WHEN YOU DON'T READ DOCs AND SKIP INTENTS AND WONDER WHY YOU BOT CAN READ YOUR MESSAGE FOR HOURS AHHHH
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)

dbx = dropbox.Dropbox(os.getenv('DROPBOX_TOKEN')) # Set-up Dropbox

# Console message to see if bot is working :3
@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

# Just a slash command test to say hello!
@bot.slash_command(name="hello", description="Say hello to the bot")
async def hello(ctx: discord.ApplicationContext):
    await ctx.respond("Hey!")

# Just a quick function to avoid rewriting getting and image
def get_random_image_path(local_path):
    if not os.path.exists(local_path):
        print(f"Error: Image folder '{local_path}' not found.")
        return None
    # Filter for common image file extensions
    image_files = [f for f in os.listdir(local_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]

    if not image_files:
        print(f"No image files found in '{local_path}'.")
        return None

    random_image_name = random.choice(image_files)
    return os.path.join(local_path, random_image_name)

# Slash command to send a random image to a channel
# To-Do Add role and channel auth. Don't want random people using this
# Make it so the image is deleted as it send it. That way no repeats
@bot.slash_command(name="send_image", description="Sends a random image from the local folder.")
async def send_image(ctx: discord.ApplicationContext):
    await ctx.defer()

    print(f"Slash command '/send_image' received from {ctx.author} in #{ctx.channel.name}.")

    image_path = get_random_image_path(IMAGE_FOLDER)
    # Send the image using ctx.followup.send() after deferring
    await ctx.followup.send(f"Here's a random image for everyone! {image_path}"
                            , file = discord.File(image_path))
    print(f"Successfully sent {image_path} to {ctx.channel.name}.")

# Slash Command that allows people to add images via discord itself in a reply!
# To-Do Add role and channel auth. Don't want random people using this
@bot.slash_command(name="upload_image", description="Uploads an image to bot's local storage.")
async def upload_image(ctx: discord.ApplicationContext, image_file: discord.Attachment):
    await ctx.defer()

    print(f"User '{ctx.author}' is attempting to upload an image to local storage.")

    # I don't know if a bot can upload an image past 8mbs, so I check here
    if image_file.size > 8000000:  # 8 MB in bytes... I think XD
        await ctx.followup.send(
            f"File is too large! Maximum allowed is 8MB. Your file is {image_file.size}",
            ephemeral=True)
    elif not image_file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        await ctx.followup.send(f"Only image files that end with '.png', '.jpg', '.jpeg', '.webp'"
                                f"are allowed.", ephemeral=True)
    else:
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        local_file_path = os.path.join(IMAGE_FOLDER, image_file.filename) # make sure the directly exist

        try:
            image = await image_file.read()

            # Write the bytes to the local file
            with open(local_file_path, 'wb') as f:
                f.write(image)
            print(f"Successfully uploaded '{image_file.filename}' to local folder at '{local_file_path}' for user '{ctx.author}'.")
            await ctx.followup.send(f"Image '{image_file.filename}' uploaded to the bot!")
        except Exception as e:
            print(f"An error occurred as you tried to upload and image: {e}")
            await ctx.followup.send(f"An unexpected error occurred during upload. Please try again later.",
                                    ephemeral=True)

# Slash Command to show a list of images to delete locally!
# To-Do Add role and channel auth. Don't want random people using this
@bot.slash_command(name="delete_image", desciption= "Shows a list of the images in local file and which you want to delete")
async def delete_image(ctx: discord.ApplicationContext):
    await ctx.defer()

    image_files = [f for f in os.listdir(IMAGE_FOLDER)]

    if not image_files:
        await ctx.followup.send("No image files found in bot's storage.")
    else:
        list_to_string = "\n".join([f"- `{f}`" for f in image_files])
        prompt = ("Here are all the files currently located in the bot:\n"
            f"{list_to_string}\n\n"
            "Please type the exact name and file type. - THIS IS CASE SENSITIVE")
        await ctx.followup.send(prompt, ephemeral=True)

        def check(message):
            # This check now ensures the message has non-empty text content
            return (message.author == ctx.author and
                    message.channel == ctx.channel and
                    message.content.strip() != "")

        try:
            response = await bot.wait_for("message", check=check, timeout=30.0)
            file_name = response.content
            print(f"File Name: {response.content} typed")

            if file_name not in image_files:
                await ctx.followup.send(f"Image '{file_name}' not found in folder.", ephemeral=True)
            else:
                full_path = os.path.join(IMAGE_FOLDER, file_name)
                try:
                    os.remove(full_path)
                    await ctx.followup.send(f"Image '{file_name}' deleted.", ephemeral=True)
                    print(f"Successfully deleted '{file_name}'.")
                except Exception as e:
                    await ctx.followup.send(f"An unexpected error occurred while deleting image: {e}. Image: '{file_name}' not found.", ephemeral=True)

        except asyncio.TimeoutError:
            await ctx.followup.send("Time out")
        except Exception as e:
            print("Major error:", e)

# A command to list images without having to delete anything
# Add a command to send a specific image later?
@bot.slash_command(name="list_images", description="List all the images if any in the image folder.")
async def list_images(ctx: discord.ApplicationContext):
    await ctx.defer()

    image_files = [f for f in os.listdir(IMAGE_FOLDER)]

    if not image_files:
        await ctx.followup.send("No image files found in bot's storage.")
    else:
        list_to_string = "\n".join([f"- `{f}`" for f in image_files])
        prompt = ("Here are all the files currently located in the bot:\n"
            f"{list_to_string}\n\n")

        await ctx.followup.send(prompt, ephemeral=True)

# A command that takes a folder in a dropbox folder and downloads the image
# Made redundant with the addition of the other functions. Might remove in final version
@bot.slash_command(name="download_image_dropbox", description="Download a dropbox image. Locally")
async def download_images_dropbox(ctx: discord.ApplicationContext):
    try:
        os.makedirs(IMAGE_FOLDER, exist_ok=True) # To make sure directory exist

        # Get the list from dropbox
        folder_content = dbx.files_list_folder(DROPBOX_IMAGES)

        for image in folder_content.entries:
            if image.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                d_file_path = image.path_display
                download_path = os.path.join(IMAGE_FOLDER, image.name)
                try:
                    dbx.files_download_to_file(download_path, d_file_path)
                except ApiError as e:
                    print(f"Error: {e}, Failed to download")
                except Exception as e:
                    print(f"Error all: {e}")
            else:
                print(f"No images found in {folder_content}")
    except ApiError as e:
        print(f"Error: {e}, could not download an image")
    except Exception as e:
        print(f"Error: {e}, What Error eeee")

    await ctx.respond(f"Downloaded images!")

# Code to make sure connection to Dropbox is working
try:
    drop = dbx.users_get_current_account()
    print(f"User: {drop.name.display_name} has been successfully logged into.")
except Exception as e:
    print(f"Error 1: {e}. Could not connect to Dropbox.")

bot.run(os.getenv('TOKEN')) # run the bot with the token