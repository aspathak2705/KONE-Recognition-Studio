import os
from pathlib import Path
import pandas as pd
from PIL import Image, ImageDraw

base_dir = Path("test_data/e2e_20_employee")
photos_dir = base_dir / "employee_photos"
photos_dir.mkdir(parents=True, exist_ok=True)

employees = [
    # Star Performer (8 employees)
    {"employee_name": "Aarav Rajesh Sharma", "award_name": "Star Performer", "designation": "Senior Systems Architect", "branch": "Bengaluru Innovation Center"},
    {"employee_name": "Priya Venkatramani", "award_name": "Star Performer", "designation": "Lead Field Quality Specialist", "branch": "Chennai Operations"},
    {"employee_name": "Rohan Kuldeep Joshi", "award_name": "Star Performer", "designation": "Principal Escalator Engineer", "branch": "Pune Tech Hub"},
    {"employee_name": "Ananya Meenakshi Iyer", "award_name": "Star Performer", "designation": "Supply Chain Operations Manager", "branch": "Hyderabad Logistics"},
    {"employee_name": "Kavita Sundaram", "award_name": "Star Performer", "designation": "Senior Commissioning Engineer", "branch": "Mumbai Metro"},
    {"employee_name": "Vikramaditya Mukherjee", "award_name": "Star Performer", "designation": "Head of Modernization Projects", "branch": "Kolkata East"},
    {"employee_name": "Siddharth Rao", "award_name": "Star Performer", "designation": "Technical Solutions Consultant", "branch": "Delhi NCR"},
    {"employee_name": "Deepika Narayanan", "award_name": "Star Performer", "designation": "Project Safety Coordinator", "branch": "Kochi Marine"},

    # Customer Excellence (7 employees)
    {"employee_name": "Amitabh Surendra Verma", "award_name": "Customer Excellence", "designation": "Key Account Service Executive", "branch": "Gurugram Corporate"},
    {"employee_name": "Sunita Balakrishnan", "award_name": "Customer Excellence", "designation": "Customer Care Operations Lead", "branch": "Bengaluru HQ"},
    {"employee_name": "Manish Pradeep Kulkarni", "award_name": "Customer Excellence", "designation": "Senior Maintenance Supervisor", "branch": "Ahmedabad Hub"},
    {"employee_name": "Meera Subramanian", "award_name": "Customer Excellence", "designation": "Client Relationship Director", "branch": "Chennai Central"},
    {"employee_name": "Harish Chandra Gupta", "award_name": "Customer Excellence", "designation": "Regional Support Specialist", "branch": "Jaipur Branch"},
    {"employee_name": "Pooja Anand Deshmukh", "award_name": "Customer Excellence", "designation": "Service Delivery Lead", "branch": "Nagpur Region"},
    {"employee_name": "Nikhil Raghavan", "award_name": "Customer Excellence", "designation": "Elevator Reliability Specialist", "branch": "Coimbatore Tech"},

    # Innovation Champion (5 employees)
    {"employee_name": "Dr. Rajeshwari Swaminathan", "award_name": "Innovation Champion", "designation": "Director of Smart Mobility AI", "branch": "Hyderabad R&D"},
    {"employee_name": "Tushar Hemant Deshpande", "award_name": "Innovation Champion", "designation": "IoT Platform Engineering Lead", "branch": "Pune Tech Hub"},
    {"employee_name": "Divya Krishnakumar", "award_name": "Innovation Champion", "designation": "Digital Twin Simulation Engineer", "branch": "Bengaluru Labs"},
    {"employee_name": "Gaurav Jayant Pathak", "award_name": "Innovation Champion", "designation": "Predictive Diagnostics Specialist", "branch": "Mumbai Tech"},
    {"employee_name": "Sneha Madhusudan Pillai", "award_name": "Innovation Champion", "designation": "Sustainable Energy Systems Lead", "branch": "Thiruvananthapuram"}
]

# Write Excel
df = pd.DataFrame(employees)
excel_path = base_dir / "employees_20.xlsx"
df.to_excel(excel_path, index=False)
print("Wrote Excel:", excel_path, "Rows:", len(df))

palette = [
    (24, 76, 120), (32, 102, 148), (44, 122, 123), (48, 92, 140),
    (60, 80, 110), (70, 110, 130), (30, 80, 90), (45, 95, 125),
    (38, 70, 115), (52, 105, 135), (28, 88, 128), (40, 115, 140),
    (35, 75, 105), (55, 98, 138), (48, 112, 128), (32, 85, 115),
    (62, 108, 142), (42, 78, 118), (50, 118, 130), (36, 92, 132)
]

for idx, emp in enumerate(employees):
    name = emp["employee_name"]
    bg_color = palette[idx % len(palette)]
    
    img = Image.new("RGB", (320, 320), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Outer portrait circle / shoulder silhouette
    draw.ellipse([80, 50, 240, 210], fill=(235, 210, 190), outline=(255, 255, 255), width=3)
    draw.chord([40, 190, 280, 390], start=0, end=180, fill=(245, 245, 250), outline=(255, 255, 255), width=3)
    
    # Monogram badge at bottom
    clean_n = name.replace("Dr. ", "").split()
    initials = (clean_n[0][0] + clean_n[-1][0]).upper()
    draw.rectangle([110, 250, 210, 290], fill=(0, 43, 73), outline=(0, 163, 224), width=2)
    draw.text((145, 262), initials, fill=(255, 255, 255))
    
    # Frame border
    draw.rectangle([5, 5, 315, 315], outline=(0, 90, 156), width=4)
    
    filename = f"{name}.jpg"
    img_path = photos_dir / filename
    img.save(img_path, format="JPEG", quality=95)

print("Generated 20 distinct synthetic photos in:", photos_dir)
