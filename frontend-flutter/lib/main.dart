// frontend-flutter/lib/main.dart
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AvestoAI - Financial Prophet',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? dashboardData;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    fetchDashboardData();
  }

  Future<void> fetchDashboardData() async {
    try {
      final response = await http.get(
        Uri.parse('http://localhost:8080/api/dashboard'),
      );

      if (response.statusCode == 200) {
        setState(() {
          dashboardData = json.decode(response.body)['data'];
          isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        isLoading = false;
        dashboardData = _getDemoData();
      });
    }
  }

  Map<String, dynamic> _getDemoData() {
    return {
      'net_worth': 910000,
      'accounts': {'savings': 180000, 'checking': 25000, 'credit_used': 45000},
      'investments': {'mutual_funds': 350000, 'stocks': 120000},
      'opportunities': {
        'opportunities': [
          {
            'title': 'High-Yield Savings Opportunity',
            'potential_annual_value': 7200,
            'description': 'Move savings to high-yield account',
            'effort_level': 'Low'
          }
        ]
      }
    };
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text('🔮 AvestoAI'),
        backgroundColor: Colors.blue[700],
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Net Worth Card
            Card(
              elevation: 4,
              color: Colors.blue[700],
              child: Padding(
                padding: EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Net Worth',
                      style: TextStyle(color: Colors.white, fontSize: 18),
                    ),
                    SizedBox(height: 8),
                    Text(
                      '₹${(dashboardData!['net_worth'] / 100000).toStringAsFixed(1)}L',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            SizedBox(height: 20),

            // Opportunities Section
            Text(
              '💡 Opportunities',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 12),

            ...dashboardData!['opportunities']['opportunities'].take(3).map<Widget>((opp) =>
              Card(
                elevation: 2,
                margin: EdgeInsets.only(bottom: 12),
                child: ListTile(
                  leading: Icon(Icons.lightbulb, color: Colors.amber),
                  title: Text(opp['title']),
                  subtitle: Text(opp['description']),
                  trailing: Text(
                    '₹${(opp['potential_annual_value'] / 1000).toStringAsFixed(0)}K/yr',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Colors.green[700],
                    ),
                  ),
                ),
              ),
            ).toList(),

            SizedBox(height: 20),

            // Decision Scorer Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => DecisionScorerScreen()),
                  );
                },
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('🎯 Score a Financial Decision'),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green[600],
                  textStyle: TextStyle(fontSize: 18),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class DecisionScorerScreen extends StatefulWidget {
  @override
  _DecisionScorerScreenState createState() => _DecisionScorerScreenState();
}

class _DecisionScorerScreenState extends State<DecisionScorerScreen> {
  final _amountController = TextEditingController();
  final _descriptionController = TextEditingController();
  Map<String, dynamic>? scoreResult;
  bool isScoring = false;

  Future<void> scoreDecision() async {
    if (_amountController.text.isEmpty || _descriptionController.text.isEmpty) {
      return;
    }

    setState(() {
      isScoring = true;
    });

    try {
      final response = await http.post(
        Uri.parse('http://localhost:8080/api/predict'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'type': 'purchase',
          'amount': int.parse(_amountController.text),
          'description': _descriptionController.text,
          'user_context': {'income': 1200000, 'savings': 180000}
        }),
      );

      if (response.statusCode == 200) {
        setState(() {
          scoreResult = json.decode(response.body)['data'];
          isScoring = false;
        });
      }
    } catch (e) {
      setState(() {
        scoreResult = {
          'score': 65,
          'explanation': 'Demo score: This purchase moderately aligns with your financial goals.',
          'alternative': 'Consider saving for 2-3 months before purchase.'
        };
        isScoring = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('🎯 Decision Scorer'),
        backgroundColor: Colors.green[700],
      ),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Get AI-powered score for your financial decisions',
              style: TextStyle(fontSize: 16, color: Colors.grey[600]),
            ),
            SizedBox(height: 20),

            TextField(
              controller: _descriptionController,
              decoration: InputDecoration(
                labelText: 'What are you considering buying?',
                hintText: 'e.g., iPhone 15 Pro, New Car, Vacation',
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 16),

            TextField(
              controller: _amountController,
              decoration: InputDecoration(
                labelText: 'Amount (₹)',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
            ),
            SizedBox(height: 20),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: isScoring ? null : scoreDecision,
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(isScoring ? 'Analyzing...' : 'Score This Decision'),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue[600],
                  textStyle: TextStyle(fontSize: 18),
                ),
              ),
            ),

            if (scoreResult != null) ...[
              SizedBox(height: 30),
              Card(
                elevation: 4,
                child: Padding(
                  padding: EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Future Self Score',
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                      ),
                      SizedBox(height: 12),

                      // Score visualization
                      Row(
                        children: [
                          Expanded(
                            child: LinearProgressIndicator(
                              value: scoreResult!['score'] / 100,
                              backgroundColor: Colors.grey[300],
                              valueColor: AlwaysStoppedAnimation<Color>(
                                scoreResult!['score'] >= 70 ? Colors.green :
                                scoreResult!['score'] >= 40 ? Colors.orange : Colors.red,
                              ),
                              minHeight: 10,
                            ),
                          ),
                          SizedBox(width: 12),
                          Text(
                            '${scoreResult!['score']}/100',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),

                      SizedBox(height: 16),
                      Text(
                        scoreResult!['explanation'],
                        style: TextStyle(fontSize: 16),
                      ),

                      if (scoreResult!['alternative'] != null) ...[
                        SizedBox(height: 12),
                        Container(
                          padding: EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.blue[50],
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Better Alternative:',
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              SizedBox(height: 4),
                              Text(scoreResult!['alternative']),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
