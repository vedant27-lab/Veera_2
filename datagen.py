import pandas as pd
from faker import Faker
import random
import numpy as np

# Initialize Faker to generate realistic fake data
fake = Faker()

def generate_uncleaned_data(num_records=1000):
    """
    Generates a DataFrame with uncleaned data for EDA practice.
    """
    data = []
    for i in range(num_records):
        # Generate some clean data first
        name = fake.name()
        email = fake.email()
        
        # Introduce inconsistent formatting for job titles
        job = fake.job()
        if random.random() < 0.2: # 20% chance of being messy
            job = job.upper() if random.random() < 0.5 else job.lower()
            
        # Introduce missing values (NaN)
        age = random.randint(18, 70)
        if random.random() < 0.15: # 15% chance of being a missing value
            age = np.nan
            
        # Introduce outliers for salary
        salary = random.randint(40000, 150000)
        if random.random() < 0.05: # 5% chance of being an outlier
            salary = random.randint(300000, 500000)
        
        # Introduce inconsistent date formats
        join_date = fake.date_of_birth(minimum_age=1, maximum_age=10)
        date_format_choice = random.choice(['%Y-%m-%d', '%d/%m/%Y', 'Month %d, %Y'])
        if date_format_choice == 'Month %d, %Y':
             join_date = join_date.strftime('%B %d, %Y')
        else:
             join_date = join_date.strftime(date_format_choice)

        data.append([name, email, job, age, salary, join_date])
        
    df = pd.DataFrame(data, columns=['Name', 'Email', 'Job Title', 'Age', 'Salary', 'Join Date'])
    
    # Introduce duplicate rows
    if num_records > 20:
        num_duplicates = int(num_records * 0.05) # 5% duplicate rows
        duplicate_indices = df.sample(n=num_duplicates).index
        duplicates_df = df.loc[duplicate_indices]
        df = pd.concat([df, duplicates_df], ignore_index=True)
        
    return df

if __name__ == "__main__":
    # Generate the dataset with 3000 records
    uncleaned_df = generate_uncleaned_data(num_records=3000)
    
    # Save it to a CSV file
    file_name = "uncleaned_employee_data.csv"
    uncleaned_df.to_csv(file_name, index=False)
    
    print(f"Successfully generated '{file_name}' with {len(uncleaned_df)} records.")
    print("\nData includes:")
    print("- Missing 'Age' values")
    print("- Inconsistent 'Job Title' casing")
    print("- Outliers in 'Salary'")
    print("- Mixed 'Join Date' formats")
    print("- Duplicate rows")