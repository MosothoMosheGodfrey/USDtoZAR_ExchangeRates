import requests
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt

# ECB historical exchange rate data URL
url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"

# Fetch XML data from the ECB's historical exchange rate feed
response = requests.get(url)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Parse XML content using ElementTree
    root = ET.fromstring(response.content)

    # Namespace used in the XML (needed to parse XML properly)
    ns = {'ns': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}

    # Extract USD and ZAR exchange rates by date
    data = []
    for cube_date in root.findall(".//ns:Cube[@time]", ns):  # Loop over dates in the XML
        date = cube_date.attrib["time"]  # Extract date
        rates = {entry.attrib["currency"]: float(entry.attrib["rate"]) for entry in cube_date.findall(".//ns:Cube[@currency]", ns)}  # Extract rates for each currency

        # Ensure both USD and ZAR exist for the date
        if "USD" in rates and "ZAR" in rates:
            usd_to_eur = rates["USD"]  # USD to EUR exchange rate
            zar_to_eur = rates["ZAR"]  # ZAR to EUR exchange rate
            usd_to_zar = zar_to_eur / usd_to_eur  # Convert USD to ZAR by using EUR as a reference
            data.append([date, usd_to_zar])  # Store the date and USD to ZAR exchange rate

    # Convert to Pandas DataFrame for easier analysis
    df = pd.DataFrame(data, columns=["InformationDate", "USDtoZAR"])  # DataFrame with date and exchange rate columns
    df["InformationDate"] = pd.to_datetime(df["InformationDate"])  # Convert Date column to datetime type for proper sorting and analysis
    df = df.sort_values(by="InformationDate")  # Sort the DataFrame by date

    # ---- Ensure All Days of the Month ---- #
    # Generate a full range of dates from the first date to today
    all_dates = pd.date_range(start=df["InformationDate"].min(), end=pd.Timestamp.today(), freq='D')

    # Merge with the existing data to ensure all dates are covered
    df_full = pd.DataFrame(all_dates, columns=["InformationDate"])

    # Merge the full date range with the existing data (left join to preserve all dates)
    df_full = pd.merge(df_full, df, on="InformationDate", how="left")

    # ---- Apply Rolling Mean (3 Days) for Missing Data ---- #
    # Apply rolling mean to fill NaN values in the 'USDtoZAR' column (using last 3 days)
    df_full['USDtoZAR_Fill'] = df_full['USDtoZAR'].fillna(df_full['USDtoZAR'].rolling(3).mean())

    # ---- Fill Remaining NaN Values Using Forward and Backward Fill ---- #
    # Use forward-fill and backward-fill to fill any remaining NaNs
    #df_full['USDtoZAR_Fill'] = df_full['USDtoZAR_Fill'].fillna(method='ffill').fillna(method='bfill')
    df_full['USDtoZAR_Fill'] = df_full['USDtoZAR_Fill'].interpolate()

    # ---- Compute Monthly Averages Using "USDtoZAR_Fill" ---- #
    df_full["YearMonth"] = df_full["InformationDate"].dt.to_period("M")  # Extract Year-Month period for aggregation
    monthly_avg_df = df_full.groupby("YearMonth")["USDtoZAR_Fill"].mean().reset_index()  # Compute average monthly exchange rates using the extrapolated column
    monthly_avg_df["YearMonth"] = monthly_avg_df["YearMonth"].astype(str)  # Convert period to string for easier reading

    # ---- Merge Daily Data and Monthly Averages ---- #
    combined_df = pd.merge(df_full, monthly_avg_df, left_on=df_full["InformationDate"].dt.to_period("M").astype(str),
                           right_on="YearMonth", how="left", suffixes=('_daily', '_monthly'))

    # Remove unnecessary columns (YearMonth)
    combined_df = combined_df.drop(columns=["YearMonth","YearMonth_daily","YearMonth_monthly"])

    # Rename columns according to your request
    combined_df = combined_df.rename(columns={
        'USDtoZAR_Fill_daily': 'USDtoZAR_Fill',
        'USDtoZAR_Fill_monthly': 'USDtoZAR_MonthlyAver'
    })

    # Save the combined DataFrame to a CSV file
    combined_df.to_csv("USDtoZAR_ExchangeRates.csv", index=False)
    print("Combined daily and monthly average exchange rates with extrapolated values saved to USDtoZAR_ExchangeRates.csv")

    # Display the combined DataFrame with all columns
    print(combined_df)

else:
    print("Failed to fetch historical exchange rate data from ECB.")

# ---- Plotting ---- #
# Plot daily exchange rate
plt.figure(figsize=(10,6))
plt.plot(combined_df['InformationDate'], combined_df['USDtoZAR'], label='USD to ZAR Exchange Rate (Daily)', color='tab:blue')
plt.xlabel('Date')
plt.ylabel('USD to ZAR')
plt.title('USD to ZAR Exchange Rate (Daily)')
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()

# Plot monthly averages
plt.figure(figsize=(10,6))
plt.plot(combined_df['InformationDate'], combined_df['USDtoZAR_MonthlyAver'], label='Monthly Average USD to ZAR', color='tab:orange')
plt.xlabel('Year-Month')
plt.ylabel('USD to ZAR (Monthly Average)')
plt.title('USD to ZAR Exchange Rate (Monthly Average)')
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()

# Show plots
plt.show()
