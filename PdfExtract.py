# winget install "Python 3.13" --accept-package-agreements
# pip install PyMuPDF

# https://www.paprikaapp.com/help/android#importrecipes
# Generate Paprika YAML from MarleySpoon recipe PDFs

import pymupdf
import math
import glob
import os
from base64 import b64encode

def GetIngredients(rect):
    #import pdb; pdb.set_trace()
    ingredients = []
    ingredientsText = page.get_textbox(rect)
    ingredientsParts = ingredientsText.split("\n")

    ingredientText = ""
    for i, ingredient in enumerate(ingredientsParts):
        if ingredient == "•":
            ingredientText = ingredientText.strip()
            ingredientText = ingredientText.replace("- ", "-")      # Cater for columns ending in - (hyphenated words)
            ingredients.append(ingredientText)
            ingredientText = ""
        elif len(ingredient) > 3:       # Skip words which are footnote annotations for allergens (e.g. 1,2)
            ingredientText += ingredient + " "

    return ingredients

# PyMuPDF words format is (x0, y0, x1, y1, "word", block_no, line_no, word_no)
indexX0 = 0
indexY0 = 1
indexX1 = 2
indexY1 = 3
indexWord = 4

# Uncomment for breakpoint - run script and use '?' - help, 'c' - continue, 'n' - next (step over), 's' - step into, 'b line#' - set breakpoint, 'q' - quit, 'variable' - print value of variable
# https://docs.python.org/3/library/pdb.html
#import pdb; pdb.set_trace()
yamlFileName = "C:\\pdf\\recipes.yml"
if os.path.exists(yamlFileName):
    os.remove(yamlFileName)

with open(yamlFileName, "w", encoding="utf-8") as yamlFile:
    files = glob.glob("C:\\pdf\\*.pdf")
    for file in files:
        doc = pymupdf.open(file)
        page = doc[0]
        titleRect = (0, 300, 390, 560)
        titleText = page.get_textbox(titleRect)
        titleText = titleText.replace("\n", " ")

        timeServingsRect = (0, 565, 390, 590)
        timeServingsText = page.get_textbox(timeServingsRect)
        timeServings = timeServingsText.split("\n")
        recipeTime = timeServings[0].replace("ca.", "").strip()
        servings = timeServings[1].replace("Servings", "").strip()

        filename = file.replace("C:\\pdf\\", "")
        indexNumEnd = filename.index("_-_")
        recipeNumber = filename[2:indexNumEnd]
        sourceUrl = "https://marleyspoon.com/media/pdf/recipe_cards/" + recipeNumber + "/" + filename

        #import pdb; pdb.set_trace()
        images = page.get_images()
        # Image reference format is (xref, smask, width, height, bpc, colorspace, alt_colorspace, name, filter, referencer)
        imageXref = images[0][0]        # XRef for first image reference on page
        image = doc.extract_image(imageXref)
        # Show image dict keys with image.keys()
        pixMap = pymupdf.Pixmap(image["image"])
        pixMap.shrink(2)        # Downscale 3600x2400 pixel MarleySpoon images to 900x600
        jpegResizedBytes = pixMap.tobytes("jpg", jpg_quality=50)
        photoBase64 = b64encode(jpegResizedBytes)
        photo = photoBase64.decode()        # Turn base64 encoded binary into a string

        page = doc[1]       # Second page
        #text = page.get_text()      # Get plain text encoded as UTF-8
        words = page.get_text("words")      # List of words on page

        # MarleySpoon region for ingredients is (x0, y0, x1, y1) = (0, 0, 200, variable) so find y1 above "What you need"
        ingredientsRect = [0, 60, 200, 0]
        whatNeedRect = [0, 0, 200, 0]
        step1Rect = (210, 0, 780, 150)
        step4Rect = [210, 300, 780, 0]

        directionsRects = [
            [205, 150, 390, 300],
            [390, 150, 580, 300],
            [580, 150, 780, 300],
            [205, 0, 390, 560],
            [205, 0, 580, 560],
            [205, 0, 780, 560],
        ]

        calories = 0
        fat = 0
        carbs = 0
        protein = 0
        for i, word in enumerate(words):
            if word[indexWord] == "What" and words[i+1][indexWord] == "you" and words[i+2][indexWord] == "need":
                ingredientsRect[indexY1] = math.floor(word[indexY0])
                whatNeedRect[indexY0] = math.ceil(word[indexY1])
            elif word[indexWord] == "Tools":
                whatNeedRect[indexY1] = math.floor(word[indexY0])
            elif word[indexWord] == "Nutrition" and words[i+1][indexWord] == "per" and words[i+2][indexWord] == "serving":
                calories = words[i+4][indexWord]
                calories = calories.replace("kcal", "").replace(",", "")
                fat = words[i+6][indexWord]
                fat = fat.replace("g", "").replace(",", "")
                carbs = words[i+8][indexWord]
                carbs = carbs.replace("g", "").replace(",", "")
                protein = words[i+10][indexWord]
                protein = protein.replace("g", "").replace(",", "")
            elif word[indexWord] == "4." and words[i-1][indexWord] != "step":
                #import pdb; pdb.set_trace()
                step4Rect[indexY1] = math.ceil(word[indexY1])
                directionsRects[3][indexY0] = step4Rect[indexY1] + 1
                directionsRects[4][indexY0] = directionsRects[3][indexY0]
                directionsRects[5][indexY0] = directionsRects[3][indexY0]
                break

        #import pdb; pdb.set_trace()
        #topStepsWords = page.get_text("words", clip=step1Rect)
        topSteps = page.get_textbox(step1Rect)
        topSteps = topSteps.split("\n")

        bottomSteps = page.get_textbox(step4Rect)
        bottomSteps = bottomSteps.split("\n")

        directions = []
        for directionRect in directionsRects:
            directionsText = page.get_textbox(directionRect)
            directionsText = directionsText.replace("\n", " ")
            directions.append(directionsText)

        #import pdb; pdb.set_trace()
        ingredients = GetIngredients(ingredientsRect)
        whatNeed = GetIngredients(whatNeedRect)
        ingredients += whatNeed

        # Generate Paprika YAML
        recipeHeader = [
            "\n",
            "- name: " + titleText + "\n",
            "  servings: " + servings + "\n",
            "  source: Marleyspoon.com\n",
            "  source_url: " + sourceUrl + "\n",
            "  total_time: " + recipeTime + "\n",
        ]

        recipeIngredients = [
            "\n",
            "  ingredients: |\n",
        ]

        for ingredient in ingredients:
            recipeIngredients.append("    " + ingredient + "\n")

        recipeNutrition = [
            "\n",
            "  nutritional_info: |\n",
            "    Calories: " + calories + " kcal\n",
            "    Fat: " + fat + " g\n",
            "    Carbs: " + carbs + " g\n",
            "    Protein: " + protein + " g\n",
        ]

        #import pdb; pdb.set_trace()
        recipeDirections = [
            "\n",
            "  directions: |\n",
            "    **" + topSteps[0] + "**\n",
            "    " + directions[0] + "\n",
            "    \n",
            "    **" + topSteps[1] + "**\n",
            "    " + directions[1] + "\n",
            "    \n",
            "    **" + topSteps[2] + "**\n",
            "    " + directions[2] + "\n",
            "    \n",
            "    **" + bottomSteps[0] + "**\n",
            "    " + directions[3] + "\n",
            "    \n",
            "    **" + bottomSteps[1] + "**\n",
            "    " + directions[4] + "\n",
            "    \n",
            "    **" + bottomSteps[2] + "**\n",
            "    " + directions[5] + "\n",
        ]

        recipePhoto = [
            "\n",
            "  photo: |\n",
            "    " + photo + "\n",
        ]

        #import pdb; pdb.set_trace()
        yamlFile.writelines(recipeHeader)
        yamlFile.writelines(recipeIngredients)
        yamlFile.writelines(recipeNutrition)
        yamlFile.writelines(recipeDirections)
        yamlFile.writelines(recipePhoto)
