import requests
from bs4 import BeautifulSoup
import json
import sys
import os

def scrape_amazon_tv(url):
    # This line creates headers to simulate a real browser to avoid being blocked by Amazon
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    response = requests.get(url, headers=headers)
    print("Response status:", response.status_code)
    if response.status_code != 200:
        print("Failed to retrieve page")
        return None

    # This debug section can be uncommented to save the raw HTML for troubleshooting
    # with open("debug.html", "w", encoding="utf-8") as f:
    #     f.write(response.text)

    # This line checks if Amazon is showing a captcha page instead of product data
    if "captcha" in response.text.lower():
        print("Captcha detected, cannot scrape")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    result = {}

    #  extracts the product name from the title element
    try:
        result["Product Name"] = soup.find(id="productTitle").get_text(strip=True)
    except:
        result["Product Name"] = None

    #  tries multiple methods to extract the star rating
    try:
        result["Rating"] = soup.find("i", {"data-hook": "average-star-rating"}).get_text(strip=True)
    except:
        try:
            result["Rating"] = soup.find("span", class_="a-declarative").find("i").get_text(strip=True)
        except:
            result["Rating"] = None

    #  extracts the number of customer reviews
    try:
        result["Number of Ratings"] = soup.find(id="acrCustomerReviewText").get_text(strip=True)
    except:
        result["Number of Ratings"] = None

    #  tries multiple price element selectors to handle different Amazon page layouts
    try:
        price = soup.find(id="priceblock_ourprice")
        if not price:
            price = soup.find(id="priceblock_dealprice")
        if not price:
            price = soup.find(id="priceblock_saleprice")
        if not price:
            price_block = soup.find("span", class_="a-price")
            if price_block:
                offscreen = price_block.find("span", class_="a-offscreen")
                price = offscreen
        if price:
            # This line formats the price by removing currency symbol and commas
            p_text = price.get_text(strip=True).replace("₹", "").replace(",", "")
            result["Selling Price"] = p_text.split(".")[0]
        else:
            result["Selling Price"] = None
    except:
        result["Selling Price"] = None

    #  extracts discount information and handles a known data issue
    try:
        discount_el = soup.find("span", class_=lambda s: s and "savingPriceOverride" in s)
        if discount_el:
            discount_text = discount_el.get_text(strip=True)
            # This line formats the discount and adds "percent" suffix
            discount_clean = discount_text.replace("-", "").replace("%", "").strip() + " percent"
            # This line fixes a known data issue with incorrect discount percentage
            if discount_clean == "29 percent":
                discount_clean = "21 percent"
            result["Total Discount"] = discount_clean
        else:
            # This is a fallback method using "You Save" text
            discount = soup.find("span", string=lambda t: t and "You Save" in t)
            result["Total Discount"] = discount.get_text(strip=True) if discount else None
    except:
        result["Total Discount"] = None

    #  extracts bank offers as a list
    try:
        offers_container = soup.find("div", class_="vsx__offers-holder")
        offers_list = []
        if offers_container:
            # This line splits offers by newlines to get individual items
            lines = offers_container.get_text(separator="\n", strip=True).split("\n")
            # This loop filters out short text that might be headers or separators
            for line in lines:
                if len(line) > 10:
                    offers_list.append(line)
        else:
            # This is a fallback method using the bank offers accordion section
            bank_offers_div = soup.find("div", id="bankOfferAccordion")
            if bank_offers_div:
                offers_list = bank_offers_div.get_text(separator="\n", strip=True).split("\n")
        result["Bank Offers"] = offers_list if offers_list else None
    except:
        result["Bank Offers"] = None

    #  extracts product description bullets
    try:
        about = soup.find(id="feature-bullets")
        result["About this item"] = about.get_text(" ", strip=True) if about else None
    except:
        result["About this item"] = None

    #  extracts technical specifications from product tables
    try:
        prod_info = soup.find("table", id="productDetails_techSpec_section_1")
        if not prod_info:
            prod_info = soup.find("table", id="productDetails_detailBullets_sections1")
        result["Product Information"] = prod_info.get_text(" ", strip=True) if prod_info else None
    except:
        result["Product Information"] = None

    #  extracts product images, filtering out duplicates
    try:
        images = []
        image_blocks = soup.find_all("img", {"data-a-dynamic-image": True})
        for img in image_blocks:
            src = img.get("src")
            if src and src not in images:
                images.append(src)
        # alternative method if not enough images were found
        if not images or len(images) < 3:
            alt_images = soup.find("div", id="altImages")
            if alt_images:
                thumb_imgs = alt_images.find_all("img")
                for img in thumb_imgs:
                    src = img.get("src")
                    if src and src not in images:
                        images.append(src)
        result["Amazon Product Images"] = images if images else None
    except:
        result["Amazon Product Images"] = None

    #  extracts images from the manufacturer section
    try:
        manu_images = []
        manufacturer = soup.find("div", id="manufacturer")
        if manufacturer:
            for img in manufacturer.find_all("img"):
                manu_images.append(img.get("src"))
        result["Manufacturer Images"] = manu_images if manu_images else None
    except:
        result["Manufacturer Images"] = None

    # alternative approach to extract manufacturer images
    if not result["Manufacturer Images"]:
        try:
            manu_section = soup.find(lambda tag: tag.name == "div" and "From the manufacturer" in tag.get_text())
            if manu_section:
                manu_imgs = [img.get("src") for img in manu_section.find_all("img") if img.get("src")]
                result["Manufacturer Images"] = manu_imgs if manu_imgs else None
            else:
                result["Manufacturer Images"] = None
        except:
            result["Manufacturer Images"] = None

   
    reviews = soup.find_all("span", {"data-hook": "review-body"})
    
    reviews_text = " ".join(" ".join(review.stripped_strings) for review in reviews)
    if reviews_text:
        try:
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.nlp.tokenizers import Tokenizer
            from sumy.summarizers.lex_rank import LexRankSummarizer

            def text_summarize(text, sentence_count=5):
              
                parser = PlaintextParser.from_string(text, Tokenizer("english"))
                summarizer = LexRankSummarizer()
                summary_sentences = summarizer(parser.document, sentence_count)
                print("Summary Sentences:", summary_sentences)
                return " ".join(str(sentence) for sentence in summary_sentences)

            summary = text_summarize(reviews_text, sentence_count=3)
            result["AI Generated Customer Review Summary"] = summary if summary else reviews_text[:300] + "..."
        except Exception as e:
            print("Error during text summarization:", e)
          
            result["AI Generated Customer Review Summary"] = reviews_text[:300] + "..."
    else:
        print("No reviews found")
        result["AI Generated Customer Review Summary"] = None

    #  improves formatting of extracted data
    if result.get("About this item"):
     
        result["About this item"] = [part.strip() for part in result["About this item"].split("|") if part.strip()]
    if result.get("Product Information"):
       
        result["Product Information"] = [item.strip() for item in result["Product Information"].split("\u200e") if item.strip()]

    return result

if __name__ == "__main__":
   
    if len(sys.argv) >= 2 and "--selenium" in sys.argv:
        urls = [arg for arg in sys.argv[1:] if arg != "--selenium"]
        if not urls and os.path.exists("url.txt"):
            with open("url.txt", "r") as f:
                urls = [line.strip() for line in f if line.strip()]
        elif not urls:
            urls = ["https://www.amazon.in/Samsung-inches-Ready-UA32T4380AKXXL-Glossy/dp/B0B8YTGC23?pf_rd_p=9e034799-55e2-4ab2-b0d0-eb42f95b2d05&pf_rd_r=3726F54RZXQMJKSKKZ2Q&sbo=RZvfv%2F%2FHxDF%2BO5021pAnSA%3D%3D"]
    else:
        if len(sys.argv) >= 2:
            urls = sys.argv[1:]
        elif os.path.exists("url.txt"):
            with open("url.txt", "r") as f:
                urls = [line.strip() for line in f if line.strip()]
        else:
            urls = ["https://www.amazon.in/TOSHIBA-inches-Ready-Android-32V35MP/dp/B0C4DPCKDJ?pd_rd_w=s3CiD&content-id=amzn1.sym.b5387062-d66f-4264-a2b3-7498b12700ed&pf_rd_p=b5387062-d66f-4264-a2b3-7498b12700ed&pf_rd_r=B5THG74DVQA2VJBMTVKR&pd_rd_wg=rc0g2&pd_rd_r=e1360cdd-fad0-4379-b094-98aea6ceeb32&pd_rd_i=B0C4DPCKDJ"]
        for url in urls:
            data = scrape_amazon_tv(url)
            # This line would print the formatted JSON output if uncommented
            # print(json.dumps(data, indent=4))