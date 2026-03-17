from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message='Success', status_code=status.HTTP_200_OK):
    """
    Standard success response format
    
    Args:
        data: Response data (dict, list, or None)
        message: Success message string
        status_code: HTTP status code (default: 200)
    
    Returns:
        Response object with standardized format
    """
    response_data = {
        'success': True,
        'message': message,
        'data': data
    }
    return Response(response_data, status=status_code)


def error_response(message='Error occurred', errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Standard error response format
    
    Args:
        message: Error message string
        errors: Detailed error information (dict, list, or None)
        status_code: HTTP status code (default: 400)
    
    Returns:
        Response object with standardized format
    """
    response_data = {
        'success': False,
        'message': message,
    }
    
    if errors is not None:
        response_data['errors'] = errors
    
    return Response(response_data, status=status_code)


def created_response(data=None, message='Created successfully', status_code=status.HTTP_201_CREATED):
    """
    Standard creation success response
    
    Args:
        data: Created resource data
        message: Success message
        status_code: HTTP status code (default: 201)
    
    Returns:
        Response object with standardized format
    """
    return success_response(data=data, message=message, status_code=status_code)


def deleted_response(message='Deleted successfully', status_code=status.HTTP_204_NO_CONTENT):
    """
    Standard deletion success response
    
    Args:
        message: Success message
        status_code: HTTP status code (default: 204)
    
    Returns:
        Response object with standardized format
    """
    return Response({'success': True, 'message': message}, status=status_code)


def unauthorized_response(message='Unauthorized access'):
    """
    Standard unauthorized response
    
    Args:
        message: Error message
    
    Returns:
        Response object with 401 status
    """
    return error_response(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


def forbidden_response(message='Forbidden'):
    """
    Standard forbidden response
    
    Args:
        message: Error message
    
    Returns:
        Response object with 403 status
    """
    return error_response(message=message, status_code=status.HTTP_403_FORBIDDEN)


def not_found_response(message='Resource not found'):
    """
    Standard not found response
    
    Args:
        message: Error message
    
    Returns:
        Response object with 404 status
    """
    return error_response(message=message, status_code=status.HTTP_404_NOT_FOUND)


def validation_error_response(errors, message='Validation error'):
    """
    Standard validation error response
    
    Args:
        errors: Validation errors dict
        message: Error message
    
    Returns:
        Response object with 400 status
    """
    return error_response(message=message, errors=errors, status_code=status.HTTP_400_BAD_REQUEST)


def server_error_response(message='Internal server error'):
    """
    Standard server error response
    
    Args:
        message: Error message
    
    Returns:
        Response object with 500 status
    """
    return error_response(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
