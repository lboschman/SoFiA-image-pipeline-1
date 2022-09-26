"""Group sources based on proximity.

This is done in such a way to minimize the amount of data to be downloaded
off remote data repositories.
"""
from typing import List

import math as m
from warnings import WarningMessage
import numpy as np


class Point:
    """A source point in the data, has x,y coordinates.

    The class also handles the admin of which points have not been assigned
    to a rectangle yet.
    """
    points: List["Point"] = []
    remaining_points: List["Point"] = []

    def __init__(self, x: float, y: float, extent: float=0) -> None:
        self.x: float = x
        self.y: float = y
        self._extent: float = extent
        Point.points.append(self)
        Point.remaining_points.append(self)

    @classmethod
    def find_central_remaining_point(cls):
        """Find the most central point of all unassigned points.

        Most central is defined as having the least total distance to all 
        other unassigned points

        :return: the most central remaining point
        :rtype: Point
        """
        distances = [cls.distance_to_other_remaining_points(p) for p in cls.remaining_points]
        central_point = cls.remaining_points[np.argmin(distances)]
        return central_point

    @classmethod
    def distance_to_other_remaining_points(cls, point):
        """Calculate total distance to all remaining points

        :param point: the point to which the distances are calculated
        :type point: Point
        :return: total euclidean distance
        :rtype: float
        """
        total_distance = sum(point.distance(p) for p in cls.remaining_points)
        return total_distance

    def distance(self, point):
        return m.sqrt((self.x - point.x)**2 + (self.y - point.y)**2)
    
    @property
    def extent(self):
        return self._extent
    
    @extent.setter
    def extent(self, value):
        if value < 0:
            raise WarningMessage("Source cannot have negative extent, \
            setting extent to absolute of provided value")
        self._extent = abs(value)
        

class Rectangle:
    rectangles: List["Rectangle"] = []
    border: float = 0.

    def __init__(self, x0: float, y0: float, dx: float, dy: float) -> None:
        self.x0 = x0
        self.y0 = y0
        self._dx = dx
        self._dy = dy
        self.points: List[Point] = []
        Rectangle.rectangles.append(self)
    
    @property
    def dx(self):
        return self._dx
    
    @dx.setter
    def dx(self, value):
        self._dx = abs(value)
    
    @property
    def dy(self):
        return self._dy
    
    @dy.setter
    def dy(self, value):
        self._dy = abs(value)
    
    def deltaxy_accomodating(self, point: Point):
        xmin_bord, xmax_bord = self.x0 + self.border, self.x0 + self.dx - self.border
        ymin_bord, ymax_bord = self.y0 + self.border, self.y0 + self.dy - self.border

        contained_within_x_border = xmin_bord <= point.x <= xmax_bord
        contained_within_y_border = ymin_bord <= point.y <= ymax_bord

        if contained_within_x_border and contained_within_y_border:
            return 0, 0
        
        delta_x = delta_y = 0

        if not contained_within_x_border:
            delta_x = abs(min([point.x - xmin_bord, point.x - xmax_bord], key=abs))
        
        if not contained_within_y_border:
        
        return delta_x, delta_y
    
    def area_increase(self, point: Point):
        # xmin_bord, xmax_bord = self.x0 + self.border, self.x0 + self.dx - self.border
        # ymin_bord, ymax_bord = self.y0 + self.border, self.y0 + self.dy - self.border

        # contained_within_x_border = xmin_bord + point.extent <= point.x <= xmax_bord - point.extent
        # contained_within_y_border = ymin_bord + point.extent <= point.y <= ymax_bord - point.extent

        # if contained_within_x_border and contained_within_y_border:
        #     return 0
        
        # delta_x = delta_y = 0

        # if not contained_within_x_border:
        #     delta_x = abs(min([point.x - point.extent - xmin_bord, point.x + point.extent - xmax_bord], key=abs))
        
        # if not contained_within_y_border:
        #     delta_y = abs(min([point.y - point.extent - ymin_bord, point.y + point.extent - ymax_bord], key=abs))

        delta_x, delta_y = self.deltaxy_accomodating(point=point)

        delta_area = delta_x * self.dy + delta_y * self.dx + delta_x * delta_y

        return delta_area

    def find_closest_remaining_point(self) -> Point:
        delta_area = [self.area_increase(p) for p in Point.remaining_points]
        min_idx = np.argmin(delta_area)
        
        closest_point = Point.remaining_points[min_idx]
        return closest_point

    @classmethod
    def find_all_closest_remaining_point(cls):
        delta_areas = [rect.area_increase(rect.find_closest_remaining_point()) for rect in cls.rectangles]
        min_idx = np.argmin(delta_areas)

        min_delta_area = delta_areas[min_idx]

        if min_delta_area > (2 * cls.border)**2:
            # create a new rectangle around the central remaining point
            cls.create_remaining_central_rect()

        else:
            # add the closest point to the corresponding rectangle
            rect = cls.rectangles[min_idx]
            rect.add_closest_point()


    @classmethod
    def create_remaining_central_rect(cls):
        central_point = Point.find_central_remaining_point()
        x0 = central_point.x - cls.border
        y0 = central_point.y - cls.border
        new_rect = Rectangle(x0, y0, 2*cls.border, 2*cls.border)

        new_rect._add_point(central_point)

    def _add_point(self, point):
        self.points.append(point)
        Point.remaining_points.remove(point)
    
    def add_point(self, point: Point):
        # xmin_bord, xmax_bord = self.x0 + self.border, self.x0 + self.dx - self.border
        # ymin_bord, ymax_bord = self.y0 + self.border, self.y0 + self.dy - self.border

        # contained_within_x_border = xmin_bord + point.extent <= point.x <= xmax_bord - point.extent
        # contained_within_y_border = ymin_bord + point.extent <= point.y <= ymax_bord - point.extent

        # if contained_within_x_border and contained_within_y_border:
        #     self._add_point(point)
        #     return None

        # delta_x = delta_y = 0

        # if not contained_within_x_border:
        #     delta_x = min([point.x - point.extent - xmin_bord, point.x + point.extent - xmax_bord], key=abs)
        #     if delta_x < 0:
        #         self.x0 += delta_x
        #     self.dx += abs(delta_x)
        
        # if not contained_within_y_border:
        #     delta_y = min([point.y - point.extent - ymin_bord, point.y + point.extent - ymax_bord], key=abs)
        #     if delta_y < 0:
        #         self.y0 += delta_y
        #     self.dy += abs(delta_y)
        
        delta_x, delta_y = self.deltaxy_accomodating(point=point)

        if not contained_within_x_border:
            delta_x = min([point.x - xmin_bord, point.x - xmax_bord], key=abs)
            if delta_x < 0:
                self.x0 += delta_x
            self.dx += abs(delta_x)
        
        if not contained_within_y_border:
            delta_y = min([point.y - ymin_bord, point.y - ymax_bord], key=abs)
            if delta_y < 0:
                self.y0 += delta_y
        
        self.dx += abs(delta_x)
            self.dy += abs(delta_y)

        self._add_point(point)
    
    def add_closest_point(self):
        closest_point = self.find_closest_remaining_point()
        self.add_point(closest_point)

    @classmethod
    def find_efficient_coverage(cls):
        cls.create_remaining_central_rect()
        while len(Point.remaining_points) > 0:
            cls.find_all_closest_remaining_point()


    

