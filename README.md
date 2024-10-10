# cs326_project
## Data Source
The data for this project was sourced from the MovieLens Dataset, we bulk downloaded four CSV files: links, movies, ratings, and tags. For the purpose of our project, we only used the ratings table since we will be doing collaborative filtering. This dataset was accessed from the MovieLens website and was last updated in September 2018. We observed that the ratings table has four columns: userId, movieId, rating, and timestamp. We also observed that there are 100,836 rows, which means that there are 100,836 ratings in total. 

## Data Exploration
We began by loading the dataset into pandas for initial exploration. This involved examining the number of unique users and movies. We discovered that the ratings table contains 9,724 unique items (movies) and 610 unique users. We then called pivot_table on our pandas dataframe to construct the user-item matrix which we could use for further exploration. We discovered that there are 100,836 cells with non-NaN values and 5,830,804 cells with NaN values in the matrix. This meant that only 1.70% of the user-item matrix was filled. We also used a 3-dimensional scatter plot to visualize the sparsity of the matrix. Since the matrix is sparse, we concluded that matrix factorization would be a well-suited tool we can use to fill up the table and make movie rating predictions.

<img width="774" alt="Screen Shot 2024-10-09 at 3 43 23 PM" src="https://github.com/user-attachments/assets/59010b16-b153-4403-b636-ec61a7c7d9b0">

(Scatter Plot visualizing sparsity of user-item matrix)

## Data Preprocessing
As mentioned above, we constructed the user-item matrix using the ratings table loaded into pandas dataframe where rows represent unique users, columns represent unique items, and cells are populated with the ratings. This user-item matrix helped our data exploration as we could visualize its sparsity. As our goal for this project was to compare and evaluate the performances of two different matrix factorization models, we wanted to train the user embedding matrix and the item embedding matrix using a training set, tune relevant hyperparameters using a validation set, and test their performances using a test set independently. We therefore shuffled and split the ratings table using the scikit-learn library with a 70:15:15 split. For our ALS model, we loaded the split dataset into PySpark dataframes, as we used the PySpark library. 

## Data Modeling
For our project, we wanted to compare the performances of a “vanilla” Stochastic Gradient Descent (SGD) model and an Alternating Least Squares model for matrix factorization. 
For the vanilla SGD model, we used the PyTorch library to first create a user embedding matrix with the shape (number of unique users, number of latent factors) and an item embedding matrix with the shape (number of unique items, number of latent factors). The hyperparameters for this model were the number of latent factors, number of epochs, and learning rate. 

In the training process, for a user and an item, we looked up their embeddings and performed element-wise multiplication followed by summing the product, which gave us the predicted rating. We then calculated the mean-squared error between the predicted rating and the label rating, which allowed us to calculate the gradient and adjust the two embedding matrices accordingly. 

For hyperparameter tuning, we varied the number of factors from 10, 20, 50, to 100, the number of epochs from 10, 50, to 100, and the learning rate from 0.001, 0.01, to 0.05. 

For comparison, we performed a grid search where we trained our SGD models on every combination of these hyperparameters, calculated their mean absolute errors, and selected the set of hyperparameters that resulted in the lowest mean absolute error. Upon comparing the performances of the models, we discovered that our model with 100 latent factors trained over 100 epochs with a 0.05 learning rate had the lowest mean absolute error of 1.07.

For the ALS model, we used the ALS implementation by the PySpark library. For the training and tuning process, we provided the ALS model with the training set and the validation set as PySpark dataframes. There were three hyperparameters to tune for this model: maximum number of iterations, regularization parameter, and rank (number of latent factors). We varied the maximum number of iterations between 10 and 20, the regularization parameter from 0.01, 0.05, and to 0.1, and the rank from 10, 20, and to 50. After training the models on different sets of these hyperparameters, we evaluated them using the validation set. As a result, the model trained for 10 maximum iterations with 0.1 as the regularization parameter, and 10 latent factors gave us the lowest mean absolute error of 0.691. 

## Data Interpretation
Then we used the best hyperparameter for each of the models to test our models, and the result for SGD was an MAE of 1.08 and an MSE of 1.80. The ALS model gave us an MAE of 0.690 and an MSE of 0.805. The ALS model has a significantly lower MAE compared to the vanilla SGD model. This means that, on average, the ALS model’s predictions are closer to the actual ratings by about 0.387 points. The ALS model also has a significantly lower MSE compared to the vanilla SGD model, indicating that the predictions by the ALS model have a lower variance and are thus more accurate overall, as MSE penalizes larger errors more heavily. 
There are two major reasons why the ALS model gave more accurate predictions than the vanilla SGD model. First, the ALS model used an alternating optimization approach where the model alternates between fixing the user matrix and adjusting for the item matrix, and vice versa, while SGD did not. The steps taken by the ALS model were determined by solving the optimization problem directly for each matrix, which we interpreted as the reason why it converged faster than the SGD model. Second, in the ALS model, L2 regularization was applied directly into the least squares problems solved at each step, while the vanilla SGD model did not utilize regularization. We observed that the ALS model benefited from a high regularization parameter (0.1), which implies that the regularization helped enhance the performance by preventing overfitting.

## Data Action
We used the ALS model with the best performing hyperparameters to implement a recommendation system that provides movie suggestions to users based on the filled user-item matrix. We wrote a function that uses the matrix to return top N movies with the highest predicted rating given a user. 
