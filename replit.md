# Time Tracking System

## Overview

This is a Flask-based electronic time tracking system designed for Brazilian businesses. The system manages employee attendance with two distinct user roles: administrators who oversee the entire system and employees who register their daily time punches. The application tracks four daily time points: arrival, lunch departure, lunch return, and final departure. It includes comprehensive reporting features and supports Portuguese language throughout the interface.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Flask**: Lightweight Python web framework chosen for rapid development and simplicity
- **Flask-Login**: Handles user session management and authentication
- **Werkzeug**: Provides password hashing and WSGI utilities

### Authentication System
- **Role-based Access Control**: Two user profiles (admin/colaborador) with distinct permissions
- **Session-based Authentication**: Uses Flask-Login for secure user sessions
- **Password Security**: Implements Werkzeug's password hashing for secure credential storage

### Database Design
- **SQLite**: File-based database for simplicity and portability
- **Two-table Schema**:
  - `usuarios`: Stores user profiles with role-based access (admin/colaborador)
  - `pontos`: Records time punches with foreign key relationships to users
- **Data Validation**: Database constraints ensure data integrity (unique logins, valid punch types)

### Frontend Architecture
- **Server-side Rendering**: Jinja2 templating with Flask for dynamic content
- **Bootstrap 5**: Responsive UI framework for consistent styling
- **Progressive Enhancement**: JavaScript adds interactivity while maintaining core functionality without it
- **Custom CSS**: Green-themed design with Portuguese business aesthetics

### Application Structure
- **Modular Design**: Separate files for routes, authentication, and database operations
- **Blueprint Pattern**: Though not explicitly using Flask blueprints, follows similar separation of concerns
- **Error Handling**: Flash messages for user feedback and form validation

### Security Features
- **CSRF Protection**: Session-based security tokens
- **Input Validation**: Form validation on both client and server side
- **Role-based Route Protection**: Login required decorators with role checking
- **Secure Session Management**: Environment-based secret keys

### Business Logic
- **Four-point Time Tracking**: Structured daily attendance (entrada, saida_almoco, volta_almoco, saida_final)
- **Audit Trail**: All punches timestamped with creation metadata
- **Flexible Observations**: Optional notes for each time punch
- **Comprehensive Reporting**: Date-range reports with employee filtering

## External Dependencies

### Frontend Libraries
- **Bootstrap 5.3.0**: UI framework loaded via CDN for responsive design
- **Font Awesome 6.4.0**: Icon library for consistent visual elements
- **JavaScript**: Vanilla JS for form validation and UI enhancements

### Python Packages
- **Flask**: Core web framework
- **Flask-Login**: User session management
- **Werkzeug**: Security utilities and WSGI support

### Database
- **SQLite3**: Built into Python standard library, no external database server required
- **File-based Storage**: Database stored as `timetracking.db` file

### Development Environment
- **Python 3.x**: Runtime environment
- **Development Server**: Flask's built-in development server configured for host='0.0.0.0'
- **Logging**: Python's built-in logging configured for DEBUG level

### Deployment Considerations
- **WSGI Compatibility**: ProxyFix middleware for deployment behind reverse proxies
- **Environment Variables**: SESSION_SECRET configurable via environment
- **Static File Serving**: Flask serves static assets (CSS, JS) in development