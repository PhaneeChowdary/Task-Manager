# repositories/activity_repository.py
import logging
from firebase_admin import firestore
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

class ActivityRepository:
    def __init__(self, db):
        self.db = db
        
    def add_activity(self, activity_data):
        """Add an activity log entry"""
        try:
            activity_ref = self.db.collection('activity').add(activity_data)
            activity_id = activity_ref[1].id
            
            logger.info(f"Added activity {activity_id} for user {activity_data.get('userId')}")
            return activity_id
        except Exception as e:
            logger.error(f"Error adding activity: {str(e)}", exc_info=True)
            raise
            
    def get_user_activities(self, user_id, limit=50):
        """Get recent activities for a user"""
        try:
            activities = []
            activities_ref = self.db.collection('activity')\
                .where('userId', '==', user_id)\
                .limit(limit)\
                .stream()
                
            for activity in activities_ref:
                activity_data = activity.to_dict()
                activity_data['id'] = activity.id
                activities.append(activity_data)
                
            # Sort activities by timestamp
            activities.sort(key=lambda x: x.get('timestamp', 0) if x.get('timestamp') else 0, reverse=True)
            
            logger.info(f"Retrieved {len(activities)} activities for user {user_id}")
            return activities
        except Exception as e:
            logger.error(f"Error retrieving activities for user {user_id}: {str(e)}", exc_info=True)
            return []
            
    def get_activity_chart_data(self, user_id):
        """Get activity data for chart (last 7 days)"""
        try:
            activities = self.get_user_activities(user_id, limit=100)
            
            # Group activities by day
            activity_dates = {}
            today = datetime.now().date()
            
            # Initialize the last 7 days with 0 counts
            for i in range(6, -1, -1):
                date = today - timedelta(days=i)
                activity_dates[date.strftime('%Y-%m-%d')] = 0
                
            # Count activities per day
            for activity in activities:
                if activity.get('timestamp'):
                    try:
                        # Handle different timestamp formats
                        if hasattr(activity['timestamp'], 'todate'):
                            # Firestore timestamp
                            activity_date = activity['timestamp'].todate().date()
                        elif isinstance(activity['timestamp'], (int, float)):
                            # Unix timestamp (seconds since epoch)
                            activity_date = datetime.fromtimestamp(activity['timestamp']).date()
                        else:
                            # String or other format
                            activity_date = datetime.fromisoformat(str(activity['timestamp'])).date()
                                
                        date_str = activity_date.strftime('%Y-%m-%d')
                            
                        # Count even if not in our 7-day window (for debugging)
                        if date_str in activity_dates:
                            activity_dates[date_str] += 1
                                
                    except Exception as e:
                        logger.error(f"Error processing timestamp: {e}, raw timestamp: {activity['timestamp']}")
                
            # Prepare chart data
            chart_labels = list(activity_dates.keys())
            chart_data = list(activity_dates.values())
            
            logger.info(f"Generated activity chart data for user {user_id}")
            return chart_labels, chart_data
        except Exception as e:
            logger.error(f"Error generating activity chart data: {str(e)}", exc_info=True)
            return [], []