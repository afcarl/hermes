#!/usr/bin/env python

from math import sqrt
from operator import add
import numpy as np

# for arrays
from sklearn.metrics import classification_report
from sklearn.metrics import mean_squared_error
from sklearn.metrics import precision_recall_fscore_support
from sklearn.metrics import confusion_matrix

# Accuracy of ratings predictions (aka regression metrics) =====================

# RMSE -----------------------------------------------------------------    

def calculate_rmse_using_rdd(y_actual, y_predicted):
    """
    Determines the Root Mean Square Error of the predictions. 

    Args:
        y_actual: actual ratings in the format of a RDD of [ (userId, itemId, actualRating) ]
        y_predicted: predicted ratings in the format of a RDD of [ (userId, itemId, predictedRating) ]

    Assumptions: 
        y_actual and y_predicted are not in order.

    """

    ratings_diff_sq = ( y_predicted.map(lambda x: ((x[0], x[1]), x[2])) ).join( y_actual.map(lambda x: ((x[0], x[1]), x[2])) ) \
        .map( lambda (_, (predictedRating, actualRating)): (predictedRating - actualRating) ** 2 ) \

    sum_ratings_diff_sq = ratings_diff_sq.reduce(add)
    num = ratings_diff_sq.count()

    return sqrt(sum_ratings_diff_sq) / float(num) 
        
def calculate_rmse_using_array(y_actual, y_predicted):
    """
    Determines the Root Mean Square Error of the predictions.

    Args: 
        y_actual: actual ratings in the format of an array of [ (userId, itemId, actualRating) ]
        y_predicted: predicted ratings in the format of an array of [ (userId, itemId, predictedRating) ]

    Assumptions:
        y_actual and y_predicted are in the same order.

    """
    return sqrt(mean_squared_error(y_actual, y_predicted))
    #return mean_squared_error(y_actual, y_predicted) ** 0.5

# MAE ------------------------------------------------------------------

def calculate_mae_using_rdd(y_actual, y_predicted):
    """
    Determines the Mean Absolute Error of the predictions.

    Args:
        y_actual: actual ratings in the format of a RDD of [ (userId, itemId, actualRating) ]
        y_predicted: predicted ratings in the format of a RDD of [ (userId, itemId, predictedRating) ]

    Assumptions:
        y_actual and y_predicted are not in order.

    """

    ratings_diff = ( y_predicted.map(lambda x: ((x[0], x[1]), x[2])) ).join( y_actual.map(lambda x: ((x[0], x[1]), x[2])) ) \
        .map( lambda (_, (predictedRating, actualRating)): abs(predictedRating - actualRating) ) \
    
    sum_ratings_diff = ratings_diff.reduce(add)
    num = ratings_diff.count()

    return sqrt(sum_ratings_diff) / float(num) 

# Accuracy of usage predictions (aka classification metrics) ===================

# Performance, Recall, Fbeta Score, Support

def calculate_prfs_using_rdd(y_actual, y_predicted):
    # TODO: it is highly dependent on the labels 
    return

def calculate_prfs_using_array(y_actual, y_predicted):
    """
    Determines the precision, recall, fscore, and support of the predictions.

    Args:
        y_actual: actual ratings in the format of an array of [ (userId, itemId, actualRating) ]
        y_predicted: predicted ratings in the format of an array of [ (userId, itemId, predictedRating) ]

    Assumptions:
        y_actual and y_predicted are in the same order. 

    """

    # precision_recall_fscore_support's extra params:
    # 3rd param: labels = [-1, 0, +1]
    # 4th param: average = 'macro' / 'micro' / 'weighted'
    return precision_recall_fscore_support(y_actual, y_predicted)

# Accuracy of rankings of items ================================================

# TODO

# ============================================================================

def predictions_to_n(y_predicted, number_recommended=10):
    """
    Sorts the predicted ratings for a user then cuts at the specified N.  Useful when calculating metrics @N

    Args:
        y_predicted: predicted ratings in the format of a RDD of [ (userId, itemId, predictedRating) ]
        number_recommended: the number of ratings desired for each user. default is set to 10 items

    Returns:
        sorted_predictions: RDD of the sorted and cut predictions in the form of of [ (userId, itemId, predictedRating) ]

    """

    sorted_predictions = y_predicted.groupBy(lambda row: row[0])\
        .map(lambda (user_id, ratings):(user_id,sort_and_cut(list(ratings),number_recommended)))\
        .map(lambda (user, ratings): ratings).flatMap(lambda x: x)

    def sort_and_cut(ratings_list, numberOfItems):
        sorted_vals = sorted(ratings_list, key=lambda ratings: ratings[2], reverse=True)
        sorted_vals = sorted_vals[:numberOfItems]
        return sorted_vals

    return sorted_predictions

def calculate_population_category_diversity(y_predicted, content_array):
    """
    Sorts the predicted ratings for a user then cuts at the specified N.  Useful when calculating metrics @N
    The higher the category diversity the better.

    Function determines the total sum of the categories for all people (rating_array).
    So for a random group of users resulting in 330 predictions in MovieLens this could look like:
        [71, 34, 11, 22, 126, 128, 0, 165, 21, 0, 35, 0, 62, 100, 5, 131, 3, 0]
    The average of each component (by total number of predictions) is then taken
        [0.21, 0.1, 0.03....0]
    The component averages are summed
        2.79
    Finally a scaling factor is utilized to take into consideration the number of categories and the average categories for an item
        0.31
    This final step is to help normalize across datasets where some may have many more/less categories and/or more/less dense item categorization

    Args:
        y_predicted: predicted ratings in the format of a RDD of [ (userId, itemId, predictedRating) ]. Should be the n predicted ratings
        content_array: content feature array of the items which should be in the format of (item [content_feature vector])

    Returns:
        cat_diversity:

    """
    ave_coverage = content_array.map(lambda (id, array): sum(array)).mean()
    rating_array_raw = y_predicted.keyBy(lambda row: row[1]).join(content_array)\
        .map(lambda (id, (rating, array)): array).collect()
    rating_array = map(sum,zip(*np.array(rating_array_raw)))
    cat_diversity = sum([r/float(len(rating_array_raw)) for r in rating_array])*ave_coverage/float(len(rating_array))

    return cat_diversity

def calculate_item_coverage(y_training_data, y_predicted):
    """
    Calculates the percentage of user-item pairs that were predicted by the algorithm.
    The training data is passed in to determine the total number of potential user-item pairs
    Then the predicted data is passed in to determine how many user-item pairs were predicted.
    It is very important to NOT pass in the sorted and cut prediction RDD and that the algorithm trys to predict all pairs
    The use the function 'cartesian' as shown in line 25 of content_based.py is helpful in that regard

    Args:
        y_training_data: the data used to train the RecSys algorithm in the format of an RDD of [ (userId, itemId, actualRating) ]
        y_predicted: predicted ratings in the format of a RDD of [ (userId, itemId, predictedRating) ].  It is important that this is not the sorted and cut prediction RDD


    Returns:
        item_coverage: value representing the percentage of user-item pairs that were able to be predicted

    """

    prediction_count = y_predicted.count()
    #obtain the number of potential users and items from the actual array as the algorithms cannot predict something that was not trained
    num_users = y_training_data.map(lambda row: row[0]).distinct().count()
    num_items = y_training_data.map(lambda row: row[1]).distinct().count()
    potential_predict = num_users*num_items
    item_coverage = prediction_count/float(potential_predict)*100

    return item_coverage

def calculate_prediction_coverage(y_actual, y_predicted):
    """
    Calculates the percentage of known user-item pairs which were predicted by the algorithm.
    It is different from the item_coverage in that only the user's actual ratings are analyzed vs all potential ratings
    In this manner it is likely that very low occuring items or users wouldn't hurt the final metric as much calculate_item_coverage will
    It is very important to NOT pass in the sorted and cut prediction RDD

    Args:
        y_actual: actual ratings in the format of an array of [ (userId, itemId, actualRating) ]
        y_predicted: predicted ratings in the format of a RDD of [ (userId, itemId, predictedRating) ].  It is important that this is not the sorted and cut prediction RDD


    Returns:
        item_coverage: value representing the percentage of user-item pairs that were able to be predicted
    """

    predictionsAndRatings = y_predicted.map(lambda x: ((x[0], x[1]), x[2])) \
      .join(y_actual.map(lambda x: ((x[0], x[1]), x[2])))

    num_found_predictions = predictionsAndRatings.count()
    num_test_set = y_actual.count()

    prediction_coverage = num_found_predictions/float(num_test_set)*100

    return prediction_coverage