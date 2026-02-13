function d = CombineVars(d, varargin)
%COMBINEVARS  - concatenate mview variables
%
%	usage:  d = CombineVars(d1, d2, ...)
%
% use this procedure to create a new mview-compatible array-of-structs variable D 
% formed by concatenating the input list of mview variables D1, D2, ... Dn
% which must have the same NAME field structure
%
% N.B. does not adjust label offsets if present

% mkt 02/15

if nargin < 2,
	eval('help CombineVars');
	return;
end

names = {d.NAME};
for vi = 1 : length(varargin),
	dd = varargin{vi};
	if length(intersect(names,{dd.NAME})) ~= length(names),
		error('incompatible input variables');
	end
	for ci = 1 : length(d),
		d(ci).SIGNAL = [d(ci).SIGNAL ; dd(ci).SIGNAL];
	end
end
