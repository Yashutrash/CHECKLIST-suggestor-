import pandas as pd
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from mlxtend.frequent_patterns import apriori, association_rules
import numpy as np
import re
from datetime import datetime, timedelta

DATA_PATH = 'data/mock_inspection_data.csv'

class SuggestionEngine:
    def __init__(self, data_path=DATA_PATH):
        self.df = pd.read_csv(data_path)

    def get_suggestions(self, inspection_type, current_template_items=None, top_n=5):
        df_type = self.df[self.df['inspection_type'] == inspection_type]
        suggestions = []
        # 1. High-failure items
        fail_rates = (
            df_type.groupby('checklist_item_text')['outcome']
            .apply(lambda x: (x == 'FAIL').mean())
            .sort_values(ascending=False)
        )
        for item, rate in fail_rates.head(top_n).items():
            if current_template_items and item in current_template_items:
                reason = f"'{item}' frequently fails in '{inspection_type}'. Consider reviewing or clarifying this item."
                suggestions.append({
                    'item': item,
                    'action': 'review',
                    'reason': reason,
                    'confidence': float(rate)
                })
            elif not current_template_items or item not in current_template_items:
                reason = f"'{item}' frequently fails in '{inspection_type}' but is not in the current template. Consider adding."
                suggestions.append({
                    'item': item,
                    'action': 'add',
                    'reason': reason,
                    'confidence': float(rate)
                })
        # 2. Items that always pass (potentially redundant)
        pass_rates = (
            df_type.groupby('checklist_item_text')['outcome']
            .apply(lambda x: (x == 'PASS').mean())
        )
        for item, rate in pass_rates.items():
            if rate > 0.98 and (not current_template_items or item in current_template_items):
                suggestions.append({
                    'item': item,
                    'action': 'remove',
                    'reason': f"'{item}' almost always passes in '{inspection_type}'; may be redundant.",
                    'confidence': float(rate)
                })
        # 3. TF-IDF-based new item extraction from comments
        fail_comments = df_type[df_type['outcome'] == 'FAIL']['comments'].dropna()
        if not fail_comments.empty:
            tfidf = TfidfVectorizer(stop_words='english', ngram_range=(1,2), max_features=20)
            tfidf_matrix = tfidf.fit_transform(fail_comments)
            top_features = np.array(tfidf.get_feature_names_out())[np.argsort(np.asarray(tfidf_matrix.sum(axis=0)).ravel())[::-1]]
            for phrase in top_features[:5]:
                if phrase not in (current_template_items or []):
                    suggestions.append({
                        'item': f'Investigate: {phrase}',
                        'action': 'new',
                        'reason': f"'{phrase}' is a common phrase in failure comments for '{inspection_type}'.",
                        'confidence': 0.7
                    })
        # 4. Clustering checklist items (suggest grouping/clarification)
        items = df_type['checklist_item_text'].unique()
        if len(items) > 2:
            vectorizer = TfidfVectorizer(stop_words='english')
            X = vectorizer.fit_transform(items)
            n_clusters = min(3, len(items))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            clusters = {i: [] for i in range(n_clusters)}
            for idx, label in enumerate(labels):
                clusters[label].append(items[idx])
            for cluster_items in clusters.values():
                if len(cluster_items) > 1:
                    suggestions.append({
                        'item': ', '.join(cluster_items),
                        'action': 'group',
                        'reason': 'These items are semantically similar and could be grouped or clarified.',
                        'confidence': 0.6
                    })
        # 5. Association rule mining for co-failure
        pivot = pd.pivot_table(df_type, index='inspection_id', columns='checklist_item_text', values='outcome', aggfunc=lambda x: (x=='FAIL').any(), fill_value=False)
        if pivot.shape[1] > 1:
            frequent = apriori(pivot, min_support=0.1, use_colnames=True)
            rules = association_rules(frequent, metric='confidence', min_threshold=0.5)
            for _, row in rules.iterrows():
                suggestions.append({
                    'item': f"If '{row['antecedents']}' fails, '{row['consequents']}' often fails too.",
                    'action': 'co-failure',
                    'reason': f"Association rule found with confidence {row['confidence']:.2f}.",
                    'confidence': float(row['confidence'])
                })
        return suggestions

    def generate_issues_from_checklist(self, checklist_items, inspection_type):
        """Generate AI issues based on checklist items and inspection type."""
        issues = []
        df_type = self.df[self.df['inspection_type'] == inspection_type]
        
        # Issue patterns based on inspection type
        issue_patterns = {
            'Quarterly HVAC Audit': {
                'maintenance': 'Regular maintenance issues',
                'efficiency': 'Energy efficiency concerns',
                'safety': 'Safety compliance issues',
                'environmental': 'Environmental impact issues'
            },
            'Monthly Safety Inspection': {
                'compliance': 'Regulatory compliance issues',
                'safety': 'Safety protocol violations',
                'training': 'Staff training gaps',
                'equipment': 'Equipment safety issues'
            },
            'Weekly Facility Check': {
                'maintenance': 'Preventive maintenance needs',
                'cleanliness': 'Hygiene and cleanliness issues',
                'security': 'Security and access control issues',
                'infrastructure': 'Building infrastructure issues'
            }
        }
        
        # Get patterns for this inspection type
        patterns = issue_patterns.get(inspection_type, {
            'general': 'General inspection issues',
            'quality': 'Quality control issues',
            'compliance': 'Compliance and regulatory issues'
        })
        
        # Analyze each checklist item for potential issues
        for item in checklist_items:
            item_lower = item.lower()
            
            # Determine issue category based on item content
            category = 'general'
            if any(word in item_lower for word in ['maintenance', 'repair', 'service']):
                category = 'maintenance'
            elif any(word in item_lower for word in ['safety', 'hazard', 'danger']):
                category = 'safety'
            elif any(word in item_lower for word in ['clean', 'hygiene', 'sanitation']):
                category = 'cleanliness'
            elif any(word in item_lower for word in ['security', 'access', 'lock']):
                category = 'security'
            elif any(word in item_lower for word in ['compliance', 'regulation', 'standard']):
                category = 'compliance'
            
            # Generate issue based on category and item
            issue_title = f"{patterns.get(category, 'General')} - {item}"
            issue_description = self._generate_issue_description(item, category, inspection_type)
            
            # Calculate confidence based on historical data
            confidence = self._calculate_issue_confidence(item, inspection_type)
            
            # Determine severity based on failure rate and category
            severity = self._determine_severity(item, category, inspection_type)
            
            issues.append({
                'title': issue_title,
                'description': issue_description,
                'checklist_item': item,
                'inspection_type': inspection_type,
                'severity': severity,
                'confidence': confidence,
                'category': category
            })
        
        # Generate additional issues based on historical patterns
        additional_issues = self._generate_pattern_based_issues(inspection_type, checklist_items)
        issues.extend(additional_issues)
        
        return issues

    def _generate_issue_description(self, item, category, inspection_type):
        """Generate detailed issue description."""
        descriptions = {
            'maintenance': f"Regular maintenance required for {item}. Historical data shows this item has frequent failure rates in {inspection_type} inspections.",
            'safety': f"Safety concern identified for {item}. This item requires immediate attention to ensure compliance with safety standards.",
            'cleanliness': f"Hygiene and cleanliness issue detected for {item}. Regular cleaning and maintenance protocols need to be established.",
            'security': f"Security vulnerability identified in {item}. Access control and security measures need to be reviewed and updated.",
            'compliance': f"Compliance issue found for {item}. Regulatory requirements need to be verified and updated procedures implemented.",
            'general': f"General issue identified for {item}. This item requires attention to maintain quality standards in {inspection_type}."
        }
        return descriptions.get(category, descriptions['general'])

    def _calculate_issue_confidence(self, item, inspection_type):
        """Calculate confidence based on historical failure rates."""
        df_type = self.df[self.df['inspection_type'] == inspection_type]
        if df_type.empty:
            return 0.5
        
        item_data = df_type[df_type['checklist_item_text'] == item]
        if item_data.empty:
            return 0.6  # Medium confidence for new items
        
        fail_rate = (item_data['outcome'] == 'FAIL').mean()
        return min(0.9, max(0.3, fail_rate + 0.2))  # Normalize between 0.3 and 0.9

    def _determine_severity(self, item, category, inspection_type):
        """Determine issue severity based on category and failure rate."""
        df_type = self.df[self.df['inspection_type'] == inspection_type]
        item_data = df_type[df_type['checklist_item_text'] == item]
        
        if item_data.empty:
            return 'medium'  # Default for new items
        
        fail_rate = (item_data['outcome'] == 'FAIL').mean()
        
        # High severity for safety issues or high failure rates
        if category == 'safety' or fail_rate > 0.7:
            return 'high'
        elif fail_rate > 0.4 or category in ['compliance', 'security']:
            return 'medium'
        else:
            return 'low'

    def _generate_pattern_based_issues(self, inspection_type, checklist_items):
        """Generate issues based on historical patterns and correlations."""
        issues = []
        df_type = self.df[self.df['inspection_type'] == inspection_type]
        
        if df_type.empty:
            return issues
        
        # Find items that frequently fail together
        pivot = pd.pivot_table(df_type, index='inspection_id', columns='checklist_item_text', 
                             values='outcome', aggfunc=lambda x: (x=='FAIL').any(), fill_value=False)
        
        if pivot.shape[1] > 1:
            # Find correlations between items
            correlations = pivot.corr()
            for i in range(len(correlations.columns)):
                for j in range(i+1, len(correlations.columns)):
                    if correlations.iloc[i, j] > 0.5:  # Strong correlation
                        item1 = correlations.columns[i]
                        item2 = correlations.columns[j]
                        
                        if item1 in checklist_items and item2 in checklist_items:
                            issues.append({
                                'title': f"Correlated Issues - {item1} and {item2}",
                                'description': f"Historical data shows that {item1} and {item2} frequently fail together. Consider addressing both items simultaneously.",
                                'checklist_item': f"{item1}, {item2}",
                                'inspection_type': inspection_type,
                                'severity': 'medium',
                                'confidence': float(correlations.iloc[i, j]),
                                'category': 'correlation'
                            })
        
        return issues

    def get_item_trends(self, checklist_item_text):
        df_item = self.df[self.df['checklist_item_text'] == checklist_item_text]
        trend = df_item.groupby('timestamp')['outcome'].value_counts().unstack().fillna(0)
        return trend.tail(30).to_dict('index')  # last 30 days

    def get_common_issues(self, inspection_type, top_n=10):
        df_type = self.df[self.df['inspection_type'] == inspection_type]
        fail_comments = df_type[df_type['outcome'] == 'FAIL']['comments']
        words = ' '.join(fail_comments.dropna()).lower().split()
        common_words = Counter(words).most_common(top_n)
        return [{'word': w, 'count': c} for w, c in common_words if len(w) > 4]

    def get_pass_fail_trends(self, inspection_type):
        """Get pass/fail trends over time for an inspection type."""
        df_type = self.df[self.df['inspection_type'] == inspection_type]
        if df_type.empty:
            return []
        
        # Group by timestamp and calculate pass/fail counts
        trends = df_type.groupby('timestamp')['outcome'].value_counts().unstack().fillna(0)
        trends = trends.reset_index()
        
        # Convert to list of dicts for charting
        return trends.to_dict('records')

    def get_top_failing_items(self, inspection_type, top_n=5):
        """Get top failing items for an inspection type."""
        df_type = self.df[self.df['inspection_type'] == inspection_type]
        if df_type.empty:
            return []
        
        # Calculate fail rates for each item
        fail_rates = (
            df_type.groupby('checklist_item_text')['outcome']
            .apply(lambda x: (x == 'FAIL').mean())
            .sort_values(ascending=False)
        )
        
        return [
            {
                'item': item,
                'fail_rate': float(rate),
                'total_inspections': int(df_type[df_type['checklist_item_text'] == item].shape[0])
            }
            for item, rate in fail_rates.head(top_n).items()
        ]

# For testing
if __name__ == '__main__':
    engine = SuggestionEngine()
    print(engine.get_suggestions('Quarterly HVAC Audit', []))
    print(engine.get_item_trends('Check fire extinguisher pressure'))
    print(engine.get_common_issues('Quarterly HVAC Audit'))
    
    # Test new AI issue generation
    test_items = ['Check HVAC filters', 'Inspect electrical panels', 'Test fire alarms']
    issues = engine.generate_issues_from_checklist(test_items, 'Quarterly HVAC Audit')
    print("\nGenerated Issues:")
    for issue in issues:
        print(f"- {issue['title']}: {issue['description']}") 