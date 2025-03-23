import nltk
nltk.download("punkt_tab")
import streamlit as st
from Amazon import scrape_amazon_tv  # Import the scraping function from Amazon.py

def display_output(data):
    if not data:
        st.error("No data scraped!")
        return
    st.header("Scraped TV Details")
    # Display text fields
    if data.get("Product Name"):
        st.subheader("Product Name")
        st.write(data["Product Name"])
    if data.get("Rating"):
        st.subheader("Rating")
        st.write(data["Rating"])
    if data.get("Number of Ratings"):
        st.subheader("Number of Ratings")
        st.write(data["Number of Ratings"])
    if data.get("Selling Price"):
        st.subheader("Selling Price")
        st.write("Rs " + data["Selling Price"])
    if data.get("Total Discount"):
        st.subheader("Total Discount")
        st.write(data["Total Discount"])
    if data.get("Bank Offers"):
        st.subheader("Bank Offers")
        if isinstance(data["Bank Offers"], list):
            for offer in data["Bank Offers"]:
                st.write(offer)
        else:
            st.write(data["Bank Offers"])
    if data.get("About this item"):
        st.subheader("About This Item")
        if isinstance(data["About this item"], list):
            for item in data["About this item"]:
                st.write(item)
        else:
            st.write(data["About this item"])
    if data.get("Product Information"):
        st.subheader("Product Information")
        if isinstance(data["Product Information"], list):
            for info in data["Product Information"]:
                st.write(info)
        else:
            st.write(data["Product Information"])
    
    # Display images with captions
    if data.get("Amazon Product Images"):
        st.subheader("Amazon Product Images")
        for idx, image in enumerate(data["Amazon Product Images"], start=1):
            # Ensure the URL is complete
            img_url = image if not image.startswith("//") else "https:" + image
            st.write(f"Image {idx}: {img_url}")
            st.image(img_url, caption=f"Image {idx}", use_container_width=True)
    if data.get("Manufacturer Images"):
        st.subheader("Manufacturer Images")
        filtered_images = [img for img in data["Manufacturer Images"] if img.lower().endswith((".jpg"))]
        for idx, image in enumerate(filtered_images[:15], start=1):
            img_url = image if not image.startswith("//") else "https:" + image
            st.write(f"Manufacturer Image {idx}: {img_url}")
            st.image(img_url, caption=f"Manufacturer Image {idx}", use_container_width=True, width=500)
    if data.get("AI Generated Customer Review Summary"):
        st.subheader("Customer Review Summary")
        st.write(data["AI Generated Customer Review Summary"])

def main():
    st.title("Amazon TV Scraper")
    st.markdown("Enter an Amazon TV link below and click **Scrape**")
    tv_link = st.text_input("TV URL", "")
    if st.button("Scrape"):
        if tv_link:
            with st.spinner("Scraping Amazon TV details..."):
                data = scrape_amazon_tv(tv_link)
            st.success("Scraping complete!")
            display_output(data)
        else:
            st.error("Please enter a valid TV URL")

if __name__ == "__main__":
    main()
