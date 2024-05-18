# -*- coding: utf-8 -*-
"""working.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/17ev-kwPs2on8OkH1Euq2lo3ARYRJxzra
"""

!pip install pyspark

import pandas as pd
from surprise import Reader, SVD, Dataset, accuracy
from surprise.model_selection import GridSearchCV, train_test_split, cross_validate
pd.set_option('display.max_columns', None)

movies_df = pd.read_csv('sample_data/movies.csv')
ratings_df = pd.read_csv('sample_data/ratings.csv')

"""# New Section"""

# Sparse user-item matrix.

user_item_matrix = ratings_df.pivot_table(index='userId', columns='movieId', values='rating')

print(user_item_matrix.head())

# Counting the total number of non-NaNs and NaNs in the user-item matrix
non_nan_count = user_item_matrix.notna().sum().sum()
nan_count = user_item_matrix.isna().sum().sum()

print("Number of non-NaN values in the matrix:", non_nan_count)
print("Number of NaN values in the matrix:", nan_count)

from sklearn.model_selection import train_test_split

train_df, temp_df = train_test_split(user_item_matrix, test_size=0.3, random_state=42)  # 70% train, 30% temp
dev_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)  # 70% train, 30% temp

import torch
import numpy as np
from torch.autograd import Variable
from torch.utils.data.dataset import Dataset
from torch.utils.data import DataLoader
from tqdm import tqdm_notebook as tqdm
import pandas as pd

class MatrixFactorization(torch.nn.Module):
    def __init__(self, n_users, n_items, n_factors=20):
        super().__init__()
        # create user embeddings
        self.user_factors = torch.nn.Embedding(n_users, n_factors)
        # create item embeddings
        self.item_factors = torch.nn.Embedding(n_items, n_factors)
        self.user_factors.weight.data.uniform_(0, 0.05)
        self.item_factors.weight.data.uniform_(0, 0.05)

    def forward(self, data):
        users, items = data[:,0], data[:,1]
        return (self.user_factors(users) * self.item_factors(items)).sum(1)

    def predict(self, user, item):
        return (self.user_factors(user) * self.item_factors(item)).sum(1)

class Loader(Dataset):
    def __init__(self, ratings_df):
        self.ratings = ratings_df.copy()
        users = ratings_df.userId.unique()
        movies = ratings_df.movieId.unique()

        self.userid2idx = {o:i for i,o in enumerate(users)}
        self.movieid2idx = {o:i for i,o in enumerate(movies)}

        self.idx2userid = {i:o for o,i in self.userid2idx.items()}
        self.idx2movieid = {i:o for o,i in self.movieid2idx.items()}

        self.ratings.movieId = ratings_df.movieId.apply(lambda x: self.movieid2idx[x])
        self.ratings.userId = ratings_df.userId.apply(lambda x: self.userid2idx[x])

        self.x = self.ratings.drop(['rating', 'timestamp'], axis=1).values
        self.y = self.ratings['rating'].values
        self.x, self.y = torch.tensor(self.x), torch.tensor(self.y)

    def __getitem__(self, index):
        return (self.x[index], self.y[index])

    def __len__(self):
        return len(self.ratings)

# Read your ratings data
ratings_df = pd.read_csv('sample_data/ratings.csv')

# Determine the number of unique users and items in your dataset
n_users = ratings_df['userId'].nunique()
n_items = ratings_df['movieId'].nunique()

# Create the model
model = MatrixFactorization(n_users, n_items, n_factors=8)

# Determine if GPU is available
cuda = torch.cuda.is_available()
if cuda:
    model = model.cuda()

# Define loss function and optimizer
loss_fn = torch.nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

# Create DataLoader
train_set = Loader(ratings_df)
train_loader = DataLoader(train_set, 128, shuffle=True)

# Train the model
num_epochs = 128
train_losses = []
train_mae = []
for epoch in range(num_epochs):
    model.train()
    total_loss = 0
    total_mae = 0
    for batch_idx, (data, target) in enumerate(train_loader):
        if cuda:
            data, target = data.cuda(), target.cuda()
        data, target = Variable(data), Variable(target)

        optimizer.zero_grad()
        output = model(data)
        loss = loss_fn(output, target.float())
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        # Calculate MAE
        mae = torch.abs(output - target.float()).mean().item()
        total_mae += mae

    train_losses.append(total_loss / (batch_idx+1))
    train_mae.append(total_mae / (batch_idx+1))

    print('Epoch [{}/{}], Loss: {:.4f}, MAE: {:.4f}'.format(epoch+1, num_epochs, train_losses[-1], train_mae[-1]))

# Plot the training loss and MAE
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 5))
plt.plot(train_losses, label='Training Loss')
plt.plot(train_mae, label='Training MAE')
plt.xlabel('Epoch')
plt.ylabel('Value')
plt.title('Training Loss and MAE')
plt.legend()
plt.show()

user_embeddings = model.user_factors.weight.data.cpu().numpy()
item_embeddings = model.item_factors.weight.data.cpu().numpy()

# Now you can view these embeddings, for example, print the first few embeddings
print("User embeddings:")
print(user_embeddings[:5])
print("Item embeddings:")
print(item_embeddings[:5])

!pip install implicit

import pandas as pd
from sklearn.model_selection import train_test_split
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql.functions import col

# Create a Spark session
spark = SparkSession.builder.appName("MovieRecommendationALS").getOrCreate()

# Load data using Pandas
ratings_df = pd.read_csv('sample_data/ratings.csv')

# Randomly shuffle the data
ratings_df = ratings_df.sample(frac=1, random_state=42).reset_index(drop=True)

# Split the data into train (70%), dev (15%), and test (15%)
train_df, temp_df = train_test_split(ratings_df, test_size=0.3, random_state=42)
dev_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)

# Convert Pandas DataFrame to Spark DataFrame
def pandas_to_spark(pandas_df):
    return spark.createDataFrame(pandas_df)

train_spark_df = pandas_to_spark(train_df)
dev_spark_df = pandas_to_spark(dev_df)
test_spark_df = pandas_to_spark(test_df)

# Ensure column types are correct
train_spark_df = train_spark_df.withColumn("userId", col("userId").cast("integer"))
train_spark_df = train_spark_df.withColumn("movieId", col("movieId").cast("integer"))
train_spark_df = train_spark_df.withColumn("rating", col("rating").cast("float"))

dev_spark_df = dev_spark_df.withColumn("userId", col("userId").cast("integer"))
dev_spark_df = dev_spark_df.withColumn("movieId", col("movieId").cast("integer"))
dev_spark_df = dev_spark_df.withColumn("rating", col("rating").cast("float"))

test_spark_df = test_spark_df.withColumn("userId", col("userId").cast("integer"))
test_spark_df = test_spark_df.withColumn("movieId", col("movieId").cast("integer"))
test_spark_df = test_spark_df.withColumn("rating", col("rating").cast("float"))

# Check for overlapping user-item pairs
train_users = train_spark_df.select("userId").distinct()
train_items = train_spark_df.select("movieId").distinct()

dev_users = dev_spark_df.select("userId").distinct()
dev_items = dev_spark_df.select("movieId").distinct()

test_users = test_spark_df.select("userId").distinct()
test_items = test_spark_df.select("movieId").distinct()

common_dev_users = dev_users.intersect(train_users)
common_dev_items = dev_items.intersect(train_items)

common_test_users = test_users.intersect(train_users)
common_test_items = test_items.intersect(train_items)

print(f"Number of common users in train and dev: {common_dev_users.count()}")
print(f"Number of common items in train and dev: {common_dev_items.count()}")

print(f"Number of common users in train and test: {common_test_users.count()}")
print(f"Number of common items in train and test: {common_test_items.count()}")

# Initialize ALS model
als = ALS(
    maxIter=10,
    regParam=0.1,
    userCol="userId",
    itemCol="movieId",
    ratingCol="rating",
    coldStartStrategy="drop"
)

# Train the model
als_model = als.fit(train_spark_df)

# Evaluate the model using RMSE
evaluator_rmse = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")

# Make predictions on the dev set
dev_predictions = als_model.transform(dev_spark_df)
dev_predictions = dev_predictions.na.drop()

if dev_predictions.count() > 0:
    rmse_dev = evaluator_rmse.evaluate(dev_predictions)
    print(f"Root-mean-square error on dev set = {rmse_dev}")
else:
    print("No predictions made on the dev set.")

# Make predictions on the test set
test_predictions = als_model.transform(test_spark_df)
test_predictions = test_predictions.na.drop()

if test_predictions.count() > 0:
    rmse_test = evaluator_rmse.evaluate(test_predictions)
    print(f"Root-mean-square error on test set = {rmse_test}")
else:
    print("No predictions made on the test set.")

# Evaluate the model using MAE
evaluator_mae = RegressionEvaluator(metricName="mae", labelCol="rating", predictionCol="prediction")

# Evaluate MAE on the dev set
if dev_predictions.count() > 0:
    mae_dev = evaluator_mae.evaluate(dev_predictions)
    print(f"Mean Absolute Error on dev set = {mae_dev}")
else:
    print("No predictions made on the dev set for MAE.")

# Evaluate MAE on the test set
if test_predictions.count() > 0:
    mae_test = evaluator_mae.evaluate(test_predictions)
    print(f"Mean Absolute Error on test set = {mae_test}")
else:
    print("No predictions made on the test set for MAE.")

# Stop the Spark session
spark.stop()

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql.functions import col

# Create a Spark session
spark = SparkSession.builder.appName("MovieRecommendationALS").getOrCreate()

# Load data using Spark
ratings_df = spark.read.csv('sample_data/ratings.csv', header=True, inferSchema=True)

# Split the data into train (70%), dev (15%), and test (15%)
train_df, temp_df = ratings_df.randomSplit([0.7, 0.3], seed=42)
dev_df, test_df = temp_df.randomSplit([0.5, 0.5], seed=42)

# Initialize ALS model
als = ALS(
    maxIter=10,
    regParam=0.1,
    userCol="userId",
    itemCol="movieId",
    ratingCol="rating",
    coldStartStrategy="drop"
)

# Train the model
als_model = als.fit(train_df)

# Evaluate the model using RMSE
evaluator_rmse = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")

# Make predictions on the dev set
dev_predictions = als_model.transform(dev_df)
dev_predictions = dev_predictions.na.drop()

if dev_predictions.count() > 0:
    rmse_dev = evaluator_rmse.evaluate(dev_predictions)
    print(f"Root-mean-square error on dev set = {rmse_dev}")
else:
    print("No predictions made on the dev set.")

# Make predictions on the test set
test_predictions = als_model.transform(test_df)
test_predictions = test_predictions.na.drop()

if test_predictions.count() > 0:
    rmse_test = evaluator_rmse.evaluate(test_predictions)
    print(f"Root-mean-square error on test set = {rmse_test}")
else:
    print("No predictions made on the test set.")

# Evaluate the model using MAE
evaluator_mae = RegressionEvaluator(metricName="mae", labelCol="rating", predictionCol="prediction")

# Evaluate MAE on the dev set
if dev_predictions.count() > 0:
    mae_dev = evaluator_mae.evaluate(dev_predictions)
    print(f"Mean Absolute Error on dev set = {mae_dev}")
else:
    print("No predictions made on the dev set for MAE.")

# Evaluate MAE on the test set
if test_predictions.count() > 0:
    mae_test = evaluator_mae.evaluate(test_predictions)
    print(f"Mean Absolute Error on test set = {mae_test}")
else:
    print("No predictions made on the test set for MAE.")

# Stop the Spark session
spark.stop()

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

# Create a Spark session
spark = SparkSession.builder.appName("MovieRecommendationALS").getOrCreate()

# Load data using Spark
ratings_df = spark.read.csv('sample_data/ratings.csv', header=True, inferSchema=True)

# Visualize the distribution of ratings
plt.figure(figsize=(8, 6))
sns.countplot(x='rating', data=ratings_df.toPandas())
plt.title('Distribution of Ratings')
plt.xlabel('Rating')
plt.ylabel('Count')
plt.show()

# Split the data into train (70%), dev (15%), and test (15%)
train_df, temp_df = ratings_df.randomSplit([0.7, 0.3], seed=42)
dev_df, test_df = temp_df.randomSplit([0.5, 0.5], seed=42)

# Initialize ALS model with maxIter = 8
als_8 = ALS(
    maxIter=8,
    regParam=0.1,
    userCol="userId",
    itemCol="movieId",
    ratingCol="rating",
    coldStartStrategy="drop"
)

# Train the model with maxIter = 8
als_model_8 = als_8.fit(train_df)

# Evaluate the model using RMSE and MAE
evaluator_rmse = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
evaluator_mae = RegressionEvaluator(metricName="mae", labelCol="rating", predictionCol="prediction")

# Make predictions on the dev set
dev_predictions_8 = als_model_8.transform(dev_df)
dev_predictions_8 = dev_predictions_8.na.drop()

# Evaluate RMSE on the dev set
rmse_dev_8 = evaluator_rmse.evaluate(dev_predictions_8)
print(f"Root-mean-square error on dev set with maxIter=8: {rmse_dev_8}")

# Evaluate MAE on the dev set
mae_dev_8 = evaluator_mae.evaluate(dev_predictions_8)
print(f"Mean Absolute Error on dev set with maxIter=8: {mae_dev_8}")

# Make predictions on the test set
test_predictions_8 = als_model_8.transform(test_df)
test_predictions_8 = test_predictions_8.na.drop()

# Evaluate RMSE on the test set
rmse_test_8 = evaluator_rmse.evaluate(test_predictions_8)
print(f"Root-mean-square error on test set with maxIter=8: {rmse_test_8}")

# Evaluate MAE on the test set
mae_test_8 = evaluator_mae.evaluate(test_predictions_8)
print(f"Mean Absolute Error on test set with maxIter=8: {mae_test_8}")

# Visualize actual ratings vs. predicted ratings on dev set
plt.figure(figsize=(8, 6))
sns.scatterplot(x='rating', y='prediction', data=dev_predictions_8.toPandas())
plt.title('Actual Ratings vs. Predicted Ratings (Dev Set)')
plt.xlabel('Actual Rating')
plt.ylabel('Predicted Rating')
plt.show()

# Visualize actual ratings vs. predicted ratings on test set
plt.figure(figsize=(8, 6))
sns.scatterplot(x='rating', y='prediction', data=test_predictions_8.toPandas())
plt.title('Actual Ratings vs. Predicted Ratings (Test Set)')
plt.xlabel('Actual Rating')
plt.ylabel('Predicted Rating')
plt.show()

# Stop the Spark session
spark.stop()